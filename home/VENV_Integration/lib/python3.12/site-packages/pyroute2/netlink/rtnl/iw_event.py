from pyroute2.netlink import nla


class iw_event(nla):
    nla_map = (
        (0xB00, 'SIOCSIWCOMMIT', 'hex'),
        (0xB01, 'SIOCGIWNAME', 'hex'),
        # Basic operations
        (0xB02, 'SIOCSIWNWID', 'hex'),
        (0xB03, 'SIOCGIWNWID', 'hex'),
        (0xB04, 'SIOCSIWFREQ', 'hex'),
        (0xB05, 'SIOCGIWFREQ', 'hex'),
        (0xB06, 'SIOCSIWMODE', 'hex'),
        (0xB07, 'SIOCGIWMODE', 'hex'),
        (0xB08, 'SIOCSIWSENS', 'hex'),
        (0xB09, 'SIOCGIWSENS', 'hex'),
        # Informative stuff
        (0xB0A, 'SIOCSIWRANGE', 'hex'),
        (0xB0B, 'SIOCGIWRANGE', 'hex'),
        (0xB0C, 'SIOCSIWPRIV', 'hex'),
        (0xB0D, 'SIOCGIWPRIV', 'hex'),
        (0xB0E, 'SIOCSIWSTATS', 'hex'),
        (0xB0F, 'SIOCGIWSTATS', 'hex'),
        # Spy support (statistics per MAC address -
        # used for Mobile IP support)
        (0xB10, 'SIOCSIWSPY', 'hex'),
        (0xB11, 'SIOCGIWSPY', 'hex'),
        (0xB12, 'SIOCSIWTHRSPY', 'hex'),
        (0xB13, 'SIOCGIWTHRSPY', 'hex'),
        # Access Point manipulation
        (0xB14, 'SIOCSIWAP', 'hex'),
        (0xB15, 'SIOCGIWAP', 'hex'),
        (0xB17, 'SIOCGIWAPLIST', 'hex'),
        (0xB18, 'SIOCSIWSCAN', 'hex'),
        (0xB19, 'SIOCGIWSCAN', 'hex'),
        # 802.11 specific support
        (0xB1A, 'SIOCSIWESSID', 'hex'),
        (0xB1B, 'SIOCGIWESSID', 'hex'),
        (0xB1C, 'SIOCSIWNICKN', 'hex'),
        (0xB1D, 'SIOCGIWNICKN', 'hex'),
        # Other parameters useful in 802.11 and
        # some other devices
        (0xB20, 'SIOCSIWRATE', 'hex'),
        (0xB21, 'SIOCGIWRATE', 'hex'),
        (0xB22, 'SIOCSIWRTS', 'hex'),
        (0xB23, 'SIOCGIWRTS', 'hex'),
        (0xB24, 'SIOCSIWFRAG', 'hex'),
        (0xB25, 'SIOCGIWFRAG', 'hex'),
        (0xB26, 'SIOCSIWTXPOW', 'hex'),
        (0xB27, 'SIOCGIWTXPOW', 'hex'),
        (0xB28, 'SIOCSIWRETRY', 'hex'),
        (0xB29, 'SIOCGIWRETRY', 'hex'),
        # Encoding stuff (scrambling, hardware security, WEP...)
        (0xB2A, 'SIOCSIWENCODE', 'hex'),
        (0xB2B, 'SIOCGIWENCODE', 'hex'),
        # Power saving stuff (power management, unicast
        # and multicast)
        (0xB2C, 'SIOCSIWPOWER', 'hex'),
        (0xB2D, 'SIOCGIWPOWER', 'hex'),
        # WPA : Generic IEEE 802.11 information element
        # (e.g., for WPA/RSN/WMM).
        (0xB30, 'SIOCSIWGENIE', 'hex'),
        (0xB31, 'SIOCGIWGENIE', 'hex'),
        # WPA : IEEE 802.11 MLME requests
        (0xB16, 'SIOCSIWMLME', 'hex'),
        # WPA : Authentication mode parameters
        (0xB32, 'SIOCSIWAUTH', 'hex'),
        (0xB33, 'SIOCGIWAUTH', 'hex'),
        # WPA : Extended version of encoding configuration
        (0xB34, 'SIOCSIWENCODEEXT', 'hex'),
        (0xB35, 'SIOCGIWENCODEEXT', 'hex'),
        # WPA2 : PMKSA cache management
        (0xB36, 'SIOCSIWPMKSA', 'hex'),
        # Events s.str.
        (0xC00, 'IWEVTXDROP', 'hex'),
        (0xC01, 'IWEVQUAL', 'hex'),
        (0xC02, 'IWEVCUSTOM', 'hex'),
        (0xC03, 'IWEVREGISTERED', 'hex'),
        (0xC04, 'IWEVEXPIRED', 'hex'),
        (0xC05, 'IWEVGENIE', 'hex'),
        (0xC06, 'IWEVMICHAELMICFAILURE', 'hex'),
        (0xC07, 'IWEVASSOCREQIE', 'hex'),
        (0xC08, 'IWEVASSOCRESPIE', 'hex'),
        (0xC09, 'IWEVPMKIDCAND', 'hex'),
    )
