# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Easier access to ID3 tags.

EasyID3 is a wrapper around mutagen.id3.ID3 to make ID3 tags appear
more like Vorbis or APEv2 tags.
"""

from typing import Callable, Dict

import mutagen.id3

from mutagen import Metadata
from mutagen._util import DictMixin, dict_match, loadfile
from mutagen.id3 import ID3, error, delete, ID3FileType


__all__ = ['EasyID3', 'Open', 'delete']


class EasyID3KeyError(KeyError, ValueError, error):
    """Raised when trying to get/set an invalid key.

    Subclasses both KeyError and ValueError for API compatibility,
    catching KeyError is preferred.
    """


class EasyID3(DictMixin, Metadata):
    """EasyID3(filething=None)

    A file with an ID3 tag.

    Like Vorbis comments, EasyID3 keys are case-insensitive ASCII
    strings. Only a subset of ID3 frames are supported by default. Use
    EasyID3.RegisterKey and its wrappers to support more.

    You can also set the GetFallback, SetFallback, and DeleteFallback
    to generic key getter/setter/deleter functions, which are called
    if no specific handler is registered for a key. Additionally,
    ListFallback can be used to supply an arbitrary list of extra
    keys. These can be set on EasyID3 or on individual instances after
    creation.

    To use an EasyID3 class with mutagen.mp3.MP3::

        from mutagen.mp3 import EasyMP3 as MP3
        MP3(filename)

    Because many of the attributes are constructed on the fly, things
    like the following will not work::

        ezid3["performer"].append("Joe")

    Instead, you must do::

        values = ezid3["performer"]
        values.append("Joe")
        ezid3["performer"] = values

    """

    Set: Dict[str, Callable] = {}
    Get: Dict[str, Callable] = {}
    Delete: Dict[str, Callable] = {}
    List: Dict[str, Callable] = {}

    # For compatibility.
    valid_keys = Get

    GetFallback = None
    SetFallback = None
    DeleteFallback = None
    ListFallback = None

    @classmethod
    def RegisterKey(cls, key,
                    getter=None, setter=None, deleter=None, lister=None):
        """Register a new key mapping.

        A key mapping is four functions, a getter, setter, deleter,
        and lister. The key may be either a string or a glob pattern.

        The getter, deleted, and lister receive an ID3 instance and
        the requested key name. The setter also receives the desired
        value, which will be a list of strings.

        The getter, setter, and deleter are used to implement __getitem__,
        __setitem__, and __delitem__.

        The lister is used to implement keys(). It should return a
        list of keys that are actually in the ID3 instance, provided
        by its associated getter.
        """
        key = key.lower()
        if getter is not None:
            cls.Get[key] = getter
        if setter is not None:
            cls.Set[key] = setter
        if deleter is not None:
            cls.Delete[key] = deleter
        if lister is not None:
            cls.List[key] = lister

    @classmethod
    def RegisterTextKey(cls, key, frameid):
        """Register a text key.

        If the key you need to register is a simple one-to-one mapping
        of ID3 frame name to EasyID3 key, then you can use this
        function::

            EasyID3.RegisterTextKey("title", "TIT2")
        """
        def getter(id3, key):
            return list(id3[frameid])

        def setter(id3, key, value):
            try:
                frame = id3[frameid]
            except KeyError:
                id3.add(mutagen.id3.Frames[frameid](encoding=3, text=value))
            else:
                frame.encoding = 3
                frame.text = value

        def deleter(id3, key):
            del id3[frameid]

        cls.RegisterKey(key, getter, setter, deleter)

    @classmethod
    def RegisterTXXXKey(cls, key, desc):
        """Register a user-defined text frame key.

        Some ID3 tags are stored in TXXX frames, which allow a
        freeform 'description' which acts as a subkey,
        e.g. TXXX:BARCODE.::

            EasyID3.RegisterTXXXKey('barcode', 'BARCODE').
        """
        frameid = "TXXX:" + desc

        def getter(id3, key):
            return list(id3[frameid])

        def setter(id3, key, value):
            enc = 0
            # Store 8859-1 if we can, per MusicBrainz spec.
            for v in value:
                if v and max(v) > u'\x7f':
                    enc = 3
                    break

            id3.add(mutagen.id3.TXXX(encoding=enc, text=value, desc=desc))

        def deleter(id3, key):
            del id3[frameid]

        cls.RegisterKey(key, getter, setter, deleter)

    def __init__(self, filename=None):
        self.__id3 = ID3()
        if filename is not None:
            self.load(filename)

    load = property(lambda s: s.__id3.load,
                    lambda s, v: setattr(s.__id3, 'load', v))

    @loadfile(writable=True, create=True)
    def save(self, filething=None, v1=1, v2_version=4, v23_sep='/',
             padding=None):
        """save(filething=None, v1=1, v2_version=4, v23_sep='/', padding=None)

        Save changes to a file.
        See :meth:`mutagen.id3.ID3.save` for more info.
        """

        if v2_version == 3:
            # EasyID3 only works with v2.4 frames, so update_to_v23() would
            # break things. We have to save a shallow copy of all tags
            # and restore it after saving. Due to CHAP/CTOC copying has
            # to be done recursively implemented in ID3Tags.
            backup = self.__id3._copy()
            try:
                self.__id3.update_to_v23()
                self.__id3.save(
                    filething, v1=v1, v2_version=v2_version, v23_sep=v23_sep,
                    padding=padding)
            finally:
                self.__id3._restore(backup)
        else:
            self.__id3.save(filething, v1=v1, v2_version=v2_version,
                            v23_sep=v23_sep, padding=padding)

    delete = property(lambda s: s.__id3.delete,
                      lambda s, v: setattr(s.__id3, 'delete', v))

    filename = property(lambda s: s.__id3.filename,
                        lambda s, fn: setattr(s.__id3, 'filename', fn))

    @property
    def size(self):
        return self.__id3.size

    def __getitem__(self, key):
        func = dict_match(self.Get, key.lower(), self.GetFallback)
        if func is not None:
            return func(self.__id3, key)
        else:
            raise EasyID3KeyError("%r is not a valid key" % key)

    def __setitem__(self, key, value):
        if isinstance(value, str):
            value = [value]
        func = dict_match(self.Set, key.lower(), self.SetFallback)
        if func is not None:
            return func(self.__id3, key, value)
        else:
            raise EasyID3KeyError("%r is not a valid key" % key)

    def __delitem__(self, key):
        func = dict_match(self.Delete, key.lower(), self.DeleteFallback)
        if func is not None:
            return func(self.__id3, key)
        else:
            raise EasyID3KeyError("%r is not a valid key" % key)

    def keys(self):
        keys = []
        for key in self.Get.keys():
            if key in self.List:
                keys.extend(self.List[key](self.__id3, key))
            elif key in self:
                keys.append(key)
        if self.ListFallback is not None:
            keys.extend(self.ListFallback(self.__id3, ""))
        return keys

    def pprint(self):
        """Print tag key=value pairs."""
        strings = []
        for key in sorted(self.keys()):
            values = self[key]
            for value in values:
                strings.append("%s=%s" % (key, value))
        return "\n".join(strings)


Open = EasyID3


def genre_get(id3, key):
    return id3["TCON"].genres


def genre_set(id3, key, value):
    try:
        frame = id3["TCON"]
    except KeyError:
        id3.add(mutagen.id3.TCON(encoding=3, text=value))
    else:
        frame.encoding = 3
        frame.genres = value


def genre_delete(id3, key):
    del id3["TCON"]


def date_get(id3, key):
    return [stamp.text for stamp in id3["TDRC"].text]


def date_set(id3, key, value):
    id3.add(mutagen.id3.TDRC(encoding=3, text=value))


def date_delete(id3, key):
    del id3["TDRC"]


def original_date_get(id3, key):
    return [stamp.text for stamp in id3["TDOR"].text]


def original_date_set(id3, key, value):
    id3.add(mutagen.id3.TDOR(encoding=3, text=value))


def original_date_delete(id3, key):
    del id3["TDOR"]


def performer_get(id3, key):
    people = []
    wanted_role = key.split(":", 1)[1]
    try:
        mcl = id3["TMCL"]
    except KeyError:
        raise KeyError(key)
    for role, person in mcl.people:
        if role == wanted_role:
            people.append(person)
    if people:
        return people
    else:
        raise KeyError(key)


def performer_set(id3, key, value):
    wanted_role = key.split(":", 1)[1]
    try:
        mcl = id3["TMCL"]
    except KeyError:
        mcl = mutagen.id3.TMCL(encoding=3, people=[])
        id3.add(mcl)
    mcl.encoding = 3
    people = [p for p in mcl.people if p[0] != wanted_role]
    for v in value:
        people.append((wanted_role, v))
    mcl.people = people


def performer_delete(id3, key):
    wanted_role = key.split(":", 1)[1]
    try:
        mcl = id3["TMCL"]
    except KeyError:
        raise KeyError(key)
    people = [p for p in mcl.people if p[0] != wanted_role]
    if people == mcl.people:
        raise KeyError(key)
    elif people:
        mcl.people = people
    else:
        del id3["TMCL"]


def performer_list(id3, key):
    try:
        mcl = id3["TMCL"]
    except KeyError:
        return []
    else:
        return list(set("performer:" + p[0] for p in mcl.people))


def musicbrainz_trackid_get(id3, key):
    return [id3["UFID:http://musicbrainz.org"].data.decode('ascii')]


def musicbrainz_trackid_set(id3, key, value):
    if len(value) != 1:
        raise ValueError("only one track ID may be set per song")
    value = value[0].encode('ascii')
    try:
        frame = id3["UFID:http://musicbrainz.org"]
    except KeyError:
        frame = mutagen.id3.UFID(owner="http://musicbrainz.org", data=value)
        id3.add(frame)
    else:
        frame.data = value


def musicbrainz_trackid_delete(id3, key):
    del id3["UFID:http://musicbrainz.org"]


def website_get(id3, key):
    urls = [frame.url for frame in id3.getall("WOAR")]
    if urls:
        return urls
    else:
        raise EasyID3KeyError(key)


def website_set(id3, key, value):
    id3.delall("WOAR")
    for v in value:
        id3.add(mutagen.id3.WOAR(url=v))


def website_delete(id3, key):
    id3.delall("WOAR")


def gain_get(id3, key):
    try:
        frame = id3["RVA2:" + key[11:-5]]
    except KeyError:
        raise EasyID3KeyError(key)
    else:
        return [u"%+f dB" % frame.gain]


def gain_set(id3, key, value):
    if len(value) != 1:
        raise ValueError(
            "there must be exactly one gain value, not %r.", value)
    gain = float(value[0].split()[0])
    try:
        frame = id3["RVA2:" + key[11:-5]]
    except KeyError:
        frame = mutagen.id3.RVA2(desc=key[11:-5], gain=0, peak=0, channel=1)
        id3.add(frame)
    frame.gain = gain


def gain_delete(id3, key):
    try:
        frame = id3["RVA2:" + key[11:-5]]
    except KeyError:
        pass
    else:
        if frame.peak:
            frame.gain = 0.0
        else:
            del id3["RVA2:" + key[11:-5]]


def peak_get(id3, key):
    try:
        frame = id3["RVA2:" + key[11:-5]]
    except KeyError:
        raise EasyID3KeyError(key)
    else:
        return [u"%f" % frame.peak]


def peak_set(id3, key, value):
    if len(value) != 1:
        raise ValueError(
            "there must be exactly one peak value, not %r.", value)
    peak = float(value[0])
    if peak >= 2 or peak < 0:
        raise ValueError("peak must be => 0 and < 2.")
    try:
        frame = id3["RVA2:" + key[11:-5]]
    except KeyError:
        frame = mutagen.id3.RVA2(desc=key[11:-5], gain=0, peak=0, channel=1)
        id3.add(frame)
    frame.peak = peak


def peak_delete(id3, key):
    try:
        frame = id3["RVA2:" + key[11:-5]]
    except KeyError:
        pass
    else:
        if frame.gain:
            frame.peak = 0.0
        else:
            del id3["RVA2:" + key[11:-5]]


def peakgain_list(id3, key):
    keys = []
    for frame in id3.getall("RVA2"):
        keys.append("replaygain_%s_gain" % frame.desc)
        keys.append("replaygain_%s_peak" % frame.desc)
    return keys

for frameid, key in {
    "TALB": "album",
    "TBPM": "bpm",
    "TCMP": "compilation",  # iTunes extension
    "TCOM": "composer",
    "TCOP": "copyright",
    "TENC": "encodedby",
    "TEXT": "lyricist",
    "TLEN": "length",
    "TMED": "media",
    "TMOO": "mood",
    "TIT1": "grouping",
    "TIT2": "title",
    "TIT3": "version",
    "TPE1": "artist",
    "TPE2": "albumartist",
    "TPE3": "conductor",
    "TPE4": "arranger",
    "TPOS": "discnumber",
    "TPUB": "organization",
    "TRCK": "tracknumber",
    "TOLY": "author",
    "TSO2": "albumartistsort",  # iTunes extension
    "TSOA": "albumsort",
    "TSOC": "composersort",  # iTunes extension
    "TSOP": "artistsort",
    "TSOT": "titlesort",
    "TSRC": "isrc",
    "TSST": "discsubtitle",
    "TLAN": "language",
}.items():
    EasyID3.RegisterTextKey(key, frameid)

EasyID3.RegisterKey("genre", genre_get, genre_set, genre_delete)
EasyID3.RegisterKey("date", date_get, date_set, date_delete)
EasyID3.RegisterKey("originaldate", original_date_get, original_date_set,
                    original_date_delete)
EasyID3.RegisterKey(
    "performer:*", performer_get, performer_set, performer_delete,
    performer_list)
EasyID3.RegisterKey("musicbrainz_trackid", musicbrainz_trackid_get,
                    musicbrainz_trackid_set, musicbrainz_trackid_delete)
EasyID3.RegisterKey("website", website_get, website_set, website_delete)
EasyID3.RegisterKey(
    "replaygain_*_gain", gain_get, gain_set, gain_delete, peakgain_list)
EasyID3.RegisterKey("replaygain_*_peak", peak_get, peak_set, peak_delete)

# At various times, information for this came from
# http://musicbrainz.org/docs/specs/metadata_tags.html
# http://bugs.musicbrainz.org/ticket/1383
# http://musicbrainz.org/doc/MusicBrainzTag
for desc, key in {
    u"MusicBrainz Artist Id": "musicbrainz_artistid",
    u"MusicBrainz Album Id": "musicbrainz_albumid",
    u"MusicBrainz Album Artist Id": "musicbrainz_albumartistid",
    u"MusicBrainz TRM Id": "musicbrainz_trmid",
    u"MusicIP PUID": "musicip_puid",
    u"MusicMagic Fingerprint": "musicip_fingerprint",
    u"MusicBrainz Album Status": "musicbrainz_albumstatus",
    u"MusicBrainz Album Type": "musicbrainz_albumtype",
    u"MusicBrainz Album Release Country": "releasecountry",
    u"MusicBrainz Disc Id": "musicbrainz_discid",
    u"ASIN": "asin",
    u"ALBUMARTISTSORT": "albumartistsort",
    u"PERFORMER": "performer",
    u"BARCODE": "barcode",
    u"CATALOGNUMBER": "catalognumber",
    u"MusicBrainz Release Track Id": "musicbrainz_releasetrackid",
    u"MusicBrainz Release Group Id": "musicbrainz_releasegroupid",
    u"MusicBrainz Work Id": "musicbrainz_workid",
    u"Acoustid Fingerprint": "acoustid_fingerprint",
    u"Acoustid Id": "acoustid_id",
}.items():
    EasyID3.RegisterTXXXKey(key, desc)


class EasyID3FileType(ID3FileType):
    """EasyID3FileType(filething=None)

    Like ID3FileType, but uses EasyID3 for tags.

    Arguments:
        filething (filething)

    Attributes:
        tags (`EasyID3`)
    """

    ID3 = EasyID3  # type: ignore
