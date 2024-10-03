# Copyright (C) 2005  Michael Urman
#               2006  Lukas Lalinsky
#               2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""ID3v2 reading and writing.

This is based off of the following references:

* http://id3.org/id3v2.4.0-structure
* http://id3.org/id3v2.4.0-frames
* http://id3.org/id3v2.3.0
* http://id3.org/id3v2-00
* http://id3.org/ID3v1

Its largest deviation from the above (versions 2.3 and 2.2) is that it
will not interpret the / characters as a separator, and will almost
always accept null separators to generate multi-valued text frames.

Because ID3 frame structure differs between frame types, each frame is
implemented as a different class (e.g. TIT2 as mutagen.id3.TIT2). Each
frame's documentation contains a list of its attributes.

Since this file's documentation is a little unwieldy, you are probably
interested in the :class:`ID3` class to start with.
"""

from ._file import ID3, ID3FileType, delete, ID3v1SaveOptions
from ._specs import Encoding, PictureType, CTOCFlags, ID3TimeStamp
from ._frames import Frames, Frames_2_2, Frame, TextFrame, UrlFrame, \
    UrlFrameU, TimeStampTextFrame, BinaryFrame, NumericPartTextFrame, \
    NumericTextFrame, PairedTextFrame
from ._util import ID3NoHeaderError, error, ID3UnsupportedVersionError
from ._id3v1 import ParseID3v1, MakeID3v1
from ._tags import ID3Tags
from ._frames import (AENC, APIC, ASPI, BUF, CHAP, CNT, COM, COMM, COMR, CRA,
    CRM, CTOC, ENCR, EQU2, ETC, ETCO, GEO, GEOB, GP1, GRID, GRP1, IPL, IPLS,
    LINK, LNK, MCDI, MCI, MLL, MLLT, MVI, MVIN, MVN, MVNM, OWNE, PCNT, PCST,
    PIC, POP, POPM, POSS, PRIV, RBUF, REV, RVA, RVA2, RVAD, RVRB, SEEK, SIGN,
    SLT, STC, SYLT, SYTC, TAL, TALB, TBP, TBPM, TCAT, TCM, TCMP, TCO, TCOM,
    TCON, TCOP, TCP, TCR, TDA, TDAT, TDEN, TDES, TDLY, TDOR, TDRC, TDRL, TDTG,
    TDY, TEN, TENC, TEXT, TFLT, TFT, TGID, TIM, TIME, TIPL, TIT1, TIT2, TIT3,
    TKE, TKEY, TKWD, TLA, TLAN, TLE, TLEN, TMCL, TMED, TMOO, TMT, TOA, TOAL,
    TOF, TOFN, TOL, TOLY, TOPE, TOR, TORY, TOT, TOWN, TP1, TP2, TP3, TP4, TPA,
    TPB, TPE1, TPE2, TPE3, TPE4, TPOS, TPRO, TPUB, TRC, TRCK, TRD, TRDA, TRK,
    TRSN, TRSO, TS2, TSA, TSC, TSI, TSIZ, TSO2, TSOA, TSOC, TSOP, TSOT, TSP,
    TSRC, TSS, TSSE, TSST, TST, TT1, TT2, TT3, TXT, TXX, TXXX, TYE, TYER, UFI,
    UFID, ULT, USER, USLT, WAF, WAR, WAS, WCM, WCOM, WCOP, WCP, WFED, WOAF,
    WOAR, WOAS, WORS, WPAY, WPB, WPUB, WXX, WXXX)

# deprecated
from ._util import ID3EncryptionUnsupportedError, ID3JunkFrameError, \
    ID3BadUnsynchData, ID3BadCompressedData, ID3TagError, ID3Warning, \
    BitPaddedInt as _BitPaddedIntForPicard

# support open(filename) as interface
Open = ID3

# flake8
ID3, ID3FileType, delete, ID3v1SaveOptions, Encoding, PictureType, CTOCFlags,
ID3TimeStamp, Frames, Frames_2_2, Frame, TextFrame, UrlFrame, UrlFrameU,
TimeStampTextFrame, BinaryFrame, NumericPartTextFrame, NumericTextFrame,
PairedTextFrame, ID3NoHeaderError, error, ID3UnsupportedVersionError,
ParseID3v1, MakeID3v1, ID3Tags, ID3EncryptionUnsupportedError,
ID3JunkFrameError, ID3BadUnsynchData, ID3BadCompressedData, ID3TagError,
ID3Warning

AENC, APIC, ASPI, BUF, CHAP, CNT, COM, COMM, COMR, CRA, CRM, CTOC, ENCR, EQU2,
ETC, ETCO, GEO, GEOB, GP1, GRID, GRP1, IPL, IPLS, LINK, LNK, MCDI, MCI, MLL,
MLLT, MVI, MVIN, MVN, MVNM, OWNE, PCNT, PCST, PIC, POP, POPM, POSS, PRIV,
RBUF, REV, RVA, RVA2, RVAD, RVRB, SEEK, SIGN, SLT, STC, SYLT, SYTC, TAL, TALB,
TBP, TBPM, TCAT, TCM, TCMP, TCO, TCOM, TCON, TCOP, TCP, TCR, TDA, TDAT, TDEN,
TDES, TDLY, TDOR, TDRC, TDRL, TDTG, TDY, TEN, TENC, TEXT, TFLT, TFT, TGID,
TIM, TIME, TIPL, TIT1, TIT2, TIT3, TKE, TKEY, TKWD, TLA, TLAN, TLE, TLEN,
TMCL, TMED, TMOO, TMT, TOA, TOAL, TOF, TOFN, TOL, TOLY, TOPE, TOR, TORY, TOT,
TOWN, TP1, TP2, TP3, TP4, TPA, TPB, TPE1, TPE2, TPE3, TPE4, TPOS, TPRO, TPUB,
TRC, TRCK, TRD, TRDA, TRK, TRSN, TRSO, TS2, TSA, TSC, TSI, TSIZ, TSO2, TSOA,
TSOC, TSOP, TSOT, TSP, TSRC, TSS, TSSE, TSST, TST, TT1, TT2, TT3, TXT, TXX,
TXXX, TYE, TYER, UFI, UFID, ULT, USER, USLT, WAF, WAR, WAS, WCM, WCOM, WCOP,
WCP, WFED, WOAF, WOAR, WOAS, WORS, WPAY, WPB, WPUB, WXX, WXXX


# Workaround for http://tickets.musicbrainz.org/browse/PICARD-833
class _DummySpecForPicard(object):
    write = None

EncodedTextSpec = MultiSpec = _DummySpecForPicard
BitPaddedInt = _BitPaddedIntForPicard


__all__ = ['ID3', 'ID3FileType', 'Frames', 'Open', 'delete']
