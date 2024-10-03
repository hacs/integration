# Copyright (C) 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from io import BytesIO

from mutagen.aac import ProgramConfigElement
from mutagen._util import BitReader, BitReaderError, cdata
from ._util import parse_full_atom
from ._atom import Atom, AtomError


class ASEntryError(Exception):
    pass


class AudioSampleEntry(object):
    """Parses an AudioSampleEntry atom.

    Private API.

    Attrs:
        channels (int): number of channels
        sample_size (int): sample size in bits
        sample_rate (int): sample rate in Hz
        bitrate (int): bits per second (0 means unknown)
        codec (string):
            audio codec, either 'mp4a[.*][.*]' (rfc6381) or 'alac'
        codec_description (string): descriptive codec name e.g. "AAC LC+SBR"

    Can raise ASEntryError.
    """

    channels = 0
    sample_size = 0
    sample_rate = 0
    bitrate = 0
    codec = None
    codec_description = None

    def __init__(self, atom, fileobj):
        ok, data = atom.read(fileobj)
        if not ok:
            raise ASEntryError("too short %r atom" % atom.name)

        fileobj = BytesIO(data)
        r = BitReader(fileobj)

        try:
            # SampleEntry
            r.skip(6 * 8)  # reserved
            r.skip(2 * 8)  # data_ref_index

            # AudioSampleEntry
            r.skip(8 * 8)  # reserved
            self.channels = r.bits(16)
            self.sample_size = r.bits(16)
            r.skip(2 * 8)  # pre_defined
            r.skip(2 * 8)  # reserved
            self.sample_rate = r.bits(32) >> 16
        except BitReaderError as e:
            raise ASEntryError(e)

        assert r.is_aligned()

        try:
            extra = Atom(fileobj)
        except AtomError as e:
            raise ASEntryError(e)

        self.codec = atom.name.decode("latin-1")
        self.codec_description = None

        if atom.name == b"mp4a" and extra.name == b"esds":
            self._parse_esds(extra, fileobj)
        elif atom.name == b"alac" and extra.name == b"alac":
            self._parse_alac(extra, fileobj)
        elif atom.name == b"ac-3" and extra.name == b"dac3":
            self._parse_dac3(extra, fileobj)

        if self.codec_description is None:
            self.codec_description = self.codec.upper()

    def _parse_dac3(self, atom, fileobj):
        # ETSI TS 102 366

        assert atom.name == b"dac3"

        ok, data = atom.read(fileobj)
        if not ok:
            raise ASEntryError("truncated %s atom" % atom.name)
        fileobj = BytesIO(data)
        r = BitReader(fileobj)

        # sample_rate in AudioSampleEntry covers values in
        # fscod2 and not just fscod, so ignore fscod here.
        try:
            r.skip(2 + 5 + 3)  # fscod, bsid, bsmod
            acmod = r.bits(3)
            lfeon = r.bits(1)
            bit_rate_code = r.bits(5)
            r.skip(5)  # reserved
        except BitReaderError as e:
            raise ASEntryError(e)

        self.channels = [2, 1, 2, 3, 3, 4, 4, 5][acmod] + lfeon

        try:
            self.bitrate = [
                32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
                224, 256, 320, 384, 448, 512, 576, 640][bit_rate_code] * 1000
        except IndexError:
            pass

    def _parse_alac(self, atom, fileobj):
        # https://alac.macosforge.org/trac/browser/trunk/
        #    ALACMagicCookieDescription.txt

        assert atom.name == b"alac"

        ok, data = atom.read(fileobj)
        if not ok:
            raise ASEntryError("truncated %s atom" % atom.name)

        try:
            version, flags, data = parse_full_atom(data)
        except ValueError as e:
            raise ASEntryError(e)

        if version != 0:
            raise ASEntryError("Unsupported version %d" % version)

        fileobj = BytesIO(data)
        r = BitReader(fileobj)

        try:
            # for some files the AudioSampleEntry values default to 44100/2chan
            # and the real info is in the alac cookie, so prefer it
            r.skip(32)  # frameLength
            compatibleVersion = r.bits(8)
            if compatibleVersion != 0:
                return
            self.sample_size = r.bits(8)
            r.skip(8 + 8 + 8)
            self.channels = r.bits(8)
            r.skip(16 + 32)
            self.bitrate = r.bits(32)
            self.sample_rate = r.bits(32)
        except BitReaderError as e:
            raise ASEntryError(e)

    def _parse_esds(self, esds, fileobj):
        assert esds.name == b"esds"

        ok, data = esds.read(fileobj)
        if not ok:
            raise ASEntryError("truncated %s atom" % esds.name)

        try:
            version, flags, data = parse_full_atom(data)
        except ValueError as e:
            raise ASEntryError(e)

        if version != 0:
            raise ASEntryError("Unsupported version %d" % version)

        fileobj = BytesIO(data)
        r = BitReader(fileobj)

        try:
            tag = r.bits(8)
            if tag != ES_Descriptor.TAG:
                raise ASEntryError("unexpected descriptor: %d" % tag)
            assert r.is_aligned()
        except BitReaderError as e:
            raise ASEntryError(e)

        try:
            decSpecificInfo = ES_Descriptor.parse(fileobj)
        except DescriptorError as e:
            raise ASEntryError(e)
        dec_conf_desc = decSpecificInfo.decConfigDescr

        self.bitrate = dec_conf_desc.avgBitrate
        self.codec += dec_conf_desc.codec_param
        self.codec_description = dec_conf_desc.codec_desc

        decSpecificInfo = dec_conf_desc.decSpecificInfo
        if decSpecificInfo is not None:
            if decSpecificInfo.channels != 0:
                self.channels = decSpecificInfo.channels

            if decSpecificInfo.sample_rate != 0:
                self.sample_rate = decSpecificInfo.sample_rate


class DescriptorError(Exception):
    pass


class BaseDescriptor(object):

    TAG: int

    @classmethod
    def _parse_desc_length_file(cls, fileobj):
        """May raise ValueError"""

        value = 0
        for i in range(4):
            try:
                b = cdata.uint8(fileobj.read(1))
            except cdata.error as e:
                raise ValueError(e)
            value = (value << 7) | (b & 0x7f)
            if not b >> 7:
                break
        else:
            raise ValueError("invalid descriptor length")

        return value

    @classmethod
    def parse(cls, fileobj):
        """Returns a parsed instance of the called type.
        The file position is right after the descriptor after this returns.

        Raises DescriptorError
        """

        try:
            length = cls._parse_desc_length_file(fileobj)
        except ValueError as e:
            raise DescriptorError(e)
        pos = fileobj.tell()
        instance = cls(fileobj, length)
        left = length - (fileobj.tell() - pos)
        if left > 0:
            fileobj.seek(left, 1)
        else:
            # XXX: In case the instance length is shorted than the content
            # assume the size is wrong and just continue parsing
            # https://github.com/quodlibet/mutagen/issues/444
            pass
        return instance


class ES_Descriptor(BaseDescriptor):

    TAG = 0x3

    def __init__(self, fileobj, length):
        """Raises DescriptorError"""

        r = BitReader(fileobj)
        try:
            self.ES_ID = r.bits(16)
            self.streamDependenceFlag = r.bits(1)
            self.URL_Flag = r.bits(1)
            self.OCRstreamFlag = r.bits(1)
            self.streamPriority = r.bits(5)
            if self.streamDependenceFlag:
                self.dependsOn_ES_ID = r.bits(16)
            if self.URL_Flag:
                URLlength = r.bits(8)
                self.URLstring = r.bytes(URLlength)
            if self.OCRstreamFlag:
                self.OCR_ES_Id = r.bits(16)

            tag = r.bits(8)
        except BitReaderError as e:
            raise DescriptorError(e)

        if tag != DecoderConfigDescriptor.TAG:
            raise DescriptorError("unexpected DecoderConfigDescrTag %d" % tag)

        assert r.is_aligned()
        self.decConfigDescr = DecoderConfigDescriptor.parse(fileobj)


class DecoderConfigDescriptor(BaseDescriptor):

    TAG = 0x4

    decSpecificInfo = None
    """A DecoderSpecificInfo, optional"""

    def __init__(self, fileobj, length):
        """Raises DescriptorError"""

        r = BitReader(fileobj)

        try:
            self.objectTypeIndication = r.bits(8)
            self.streamType = r.bits(6)
            self.upStream = r.bits(1)
            self.reserved = r.bits(1)
            self.bufferSizeDB = r.bits(24)
            self.maxBitrate = r.bits(32)
            self.avgBitrate = r.bits(32)

            if (self.objectTypeIndication, self.streamType) != (0x40, 0x5):
                return

            # all from here is optional
            if length * 8 == r.get_position():
                return

            tag = r.bits(8)
        except BitReaderError as e:
            raise DescriptorError(e)

        if tag == DecoderSpecificInfo.TAG:
            assert r.is_aligned()
            self.decSpecificInfo = DecoderSpecificInfo.parse(fileobj)

    @property
    def codec_param(self):
        """string"""

        param = u".%X" % self.objectTypeIndication
        info = self.decSpecificInfo
        if info is not None:
            param += u".%d" % info.audioObjectType
        return param

    @property
    def codec_desc(self):
        """string or None"""

        info = self.decSpecificInfo
        desc = None
        if info is not None:
            desc = info.description
        return desc


class DecoderSpecificInfo(BaseDescriptor):

    TAG = 0x5

    _TYPE_NAMES = [
        None, "AAC MAIN", "AAC LC", "AAC SSR", "AAC LTP", "SBR",
        "AAC scalable", "TwinVQ", "CELP", "HVXC", None, None, "TTSI",
        "Main synthetic", "Wavetable synthesis", "General MIDI",
        "Algorithmic Synthesis and Audio FX", "ER AAC LC", None, "ER AAC LTP",
        "ER AAC scalable", "ER Twin VQ", "ER BSAC", "ER AAC LD", "ER CELP",
        "ER HVXC", "ER HILN", "ER Parametric", "SSC", "PS", "MPEG Surround",
        None, "Layer-1", "Layer-2", "Layer-3", "DST", "ALS", "SLS",
        "SLS non-core", "ER AAC ELD", "SMR Simple", "SMR Main", "USAC",
        "SAOC", "LD MPEG Surround", "USAC"
    ]

    _FREQS = [
        96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000,
        12000, 11025, 8000, 7350,
    ]

    @property
    def description(self):
        """string or None if unknown"""

        name = None
        try:
            name = self._TYPE_NAMES[self.audioObjectType]
        except IndexError:
            pass
        if name is None:
            return
        if self.sbrPresentFlag == 1:
            name += "+SBR"
        if self.psPresentFlag == 1:
            name += "+PS"
        return str(name)

    @property
    def sample_rate(self):
        """0 means unknown"""

        if self.sbrPresentFlag == 1:
            return self.extensionSamplingFrequency
        elif self.sbrPresentFlag == 0:
            return self.samplingFrequency
        else:
            # these are all types that support SBR
            aot_can_sbr = (1, 2, 3, 4, 6, 17, 19, 20, 22)
            if self.audioObjectType not in aot_can_sbr:
                return self.samplingFrequency
            # there shouldn't be SBR for > 48KHz
            if self.samplingFrequency > 24000:
                return self.samplingFrequency
            # either samplingFrequency or samplingFrequency * 2
            return 0

    @property
    def channels(self):
        """channel count or 0 for unknown"""

        # from ProgramConfigElement()
        if hasattr(self, "pce_channels"):
            return self.pce_channels

        conf = getattr(
            self, "extensionChannelConfiguration", self.channelConfiguration)

        if conf == 1:
            if self.psPresentFlag == -1:
                return 0
            elif self.psPresentFlag == 1:
                return 2
            else:
                return 1
        elif conf == 7:
            return 8
        elif conf > 7:
            return 0
        else:
            return conf

    def _get_audio_object_type(self, r):
        """Raises BitReaderError"""

        audioObjectType = r.bits(5)
        if audioObjectType == 31:
            audioObjectTypeExt = r.bits(6)
            audioObjectType = 32 + audioObjectTypeExt
        return audioObjectType

    def _get_sampling_freq(self, r):
        """Raises BitReaderError"""

        samplingFrequencyIndex = r.bits(4)
        if samplingFrequencyIndex == 0xf:
            samplingFrequency = r.bits(24)
        else:
            try:
                samplingFrequency = self._FREQS[samplingFrequencyIndex]
            except IndexError:
                samplingFrequency = 0
        return samplingFrequency

    def __init__(self, fileobj, length):
        """Raises DescriptorError"""

        r = BitReader(fileobj)
        try:
            self._parse(r, length)
        except BitReaderError as e:
            raise DescriptorError(e)

    def _parse(self, r, length):
        """Raises BitReaderError"""

        def bits_left():
            return length * 8 - r.get_position()

        self.audioObjectType = self._get_audio_object_type(r)
        self.samplingFrequency = self._get_sampling_freq(r)
        self.channelConfiguration = r.bits(4)

        self.sbrPresentFlag = -1
        self.psPresentFlag = -1
        if self.audioObjectType in (5, 29):
            self.extensionAudioObjectType = 5
            self.sbrPresentFlag = 1
            if self.audioObjectType == 29:
                self.psPresentFlag = 1
            self.extensionSamplingFrequency = self._get_sampling_freq(r)
            self.audioObjectType = self._get_audio_object_type(r)
            if self.audioObjectType == 22:
                self.extensionChannelConfiguration = r.bits(4)
        else:
            self.extensionAudioObjectType = 0

        if self.audioObjectType in (1, 2, 3, 4, 6, 7, 17, 19, 20, 21, 22, 23):
            try:
                GASpecificConfig(r, self)
            except NotImplementedError:
                # unsupported, (warn?)
                return
        else:
            # unsupported
            return

        if self.audioObjectType in (
                17, 19, 20, 21, 22, 23, 24, 25, 26, 27, 39):
            epConfig = r.bits(2)
            if epConfig in (2, 3):
                # unsupported
                return

        if self.extensionAudioObjectType != 5 and bits_left() >= 16:
            syncExtensionType = r.bits(11)
            if syncExtensionType == 0x2b7:
                self.extensionAudioObjectType = self._get_audio_object_type(r)

                if self.extensionAudioObjectType == 5:
                    self.sbrPresentFlag = r.bits(1)
                    if self.sbrPresentFlag == 1:
                        self.extensionSamplingFrequency = \
                            self._get_sampling_freq(r)
                        if bits_left() >= 12:
                            syncExtensionType = r.bits(11)
                            if syncExtensionType == 0x548:
                                self.psPresentFlag = r.bits(1)

                if self.extensionAudioObjectType == 22:
                    self.sbrPresentFlag = r.bits(1)
                    if self.sbrPresentFlag == 1:
                        self.extensionSamplingFrequency = \
                            self._get_sampling_freq(r)
                    self.extensionChannelConfiguration = r.bits(4)


def GASpecificConfig(r, info):
    """Reads GASpecificConfig which is needed to get the data after that
    (there is no length defined to skip it) and to read program_config_element
    which can contain channel counts.

    May raise BitReaderError on error or
    NotImplementedError if some reserved data was set.
    """

    assert isinstance(info, DecoderSpecificInfo)

    r.skip(1)  # frameLengthFlag
    dependsOnCoreCoder = r.bits(1)
    if dependsOnCoreCoder:
        r.skip(14)
    extensionFlag = r.bits(1)
    if not info.channelConfiguration:
        pce = ProgramConfigElement(r)
        info.pce_channels = pce.channels
    if info.audioObjectType == 6 or info.audioObjectType == 20:
        r.skip(3)
    if extensionFlag:
        if info.audioObjectType == 22:
            r.skip(5 + 11)
        if info.audioObjectType in (17, 19, 20, 23):
            r.skip(1 + 1 + 1)
        extensionFlag3 = r.bits(1)
        if extensionFlag3 != 0:
            raise NotImplementedError("extensionFlag3 set")
