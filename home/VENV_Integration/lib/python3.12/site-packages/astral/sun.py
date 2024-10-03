import datetime
from math import (
    acos,
    asin,
    atan2,
    cos,
    degrees,
    fabs,
    floor,
    radians,
    sin,
    sqrt,
    tan,
)
from typing import Dict, Optional, Tuple, Union

import pytz

from astral import Depression, Observer, SunDirection, now, today

__all__ = [
    "sun",
    "dawn",
    "sunrise",
    "noon",
    "midnight",
    "sunset",
    "dusk",
    "daylight",
    "night",
    "twilight",
    "blue_hour",
    "golden_hour",
    "rahukaalam",
    "zenith",
    "azimuth",
    "elevation",
    "time_at_elevation",
]


# Using 32 arc minutes as sun's apparent diameter
SUN_APPARENT_RADIUS = 32.0 / (60.0 * 2.0)


def julianday(date: datetime.date) -> float:
    """Calculate the Julian Day for the specified date"""
    y = date.year
    m = date.month
    d = date.day

    if m <= 2:
        y -= 1
        m += 12

    a = floor(y / 100)
    b = 2 - a + floor(a / 4)
    jd = floor(365.25 * (y + 4716)) + floor(30.6001 * (m + 1)) + d + b - 1524.5

    return jd


def minutes_to_timedelta(minutes: float) -> datetime.timedelta:
    """Convert a floating point number of minutes to a :class:`~datetime.timedelta`"""
    d = int(minutes / 1440)
    minutes = minutes - (d * 1440)
    minutes = minutes * 60
    s = int(minutes)
    sfrac = minutes - s
    us = int(sfrac * 1_000_000)

    return datetime.timedelta(days=d, seconds=s, microseconds=us)


def jday_to_jcentury(julianday: float) -> float:
    """Convert a Julian Day number to a Julian Century"""
    return (julianday - 2451545.0) / 36525.0


def jcentury_to_jday(juliancentury: float) -> float:
    """Convert a Julian Century number to a Julian Day"""
    return (juliancentury * 36525.0) + 2451545.0


def geom_mean_long_sun(juliancentury: float) -> float:
    """Calculate the geometric mean longitude of the sun"""
    l0 = 280.46646 + juliancentury * (36000.76983 + 0.0003032 * juliancentury)
    return l0 % 360.0


def geom_mean_anomaly_sun(juliancentury: float) -> float:
    """Calculate the geometric mean anomaly of the sun"""
    return 357.52911 + juliancentury * (35999.05029 - 0.0001537 * juliancentury)


def eccentric_location_earth_orbit(juliancentury: float) -> float:
    """Calculate the eccentricity of Earth's orbit"""
    return 0.016708634 - juliancentury * (0.000042037 + 0.0000001267 * juliancentury)


def sun_eq_of_center(juliancentury: float) -> float:
    """Calculate the equation of the center of the sun"""
    m = geom_mean_anomaly_sun(juliancentury)

    mrad = radians(m)
    sinm = sin(mrad)
    sin2m = sin(mrad + mrad)
    sin3m = sin(mrad + mrad + mrad)

    c = (
        sinm * (1.914602 - juliancentury * (0.004817 + 0.000014 * juliancentury))
        + sin2m * (0.019993 - 0.000101 * juliancentury)
        + sin3m * 0.000289
    )

    return c


def sun_true_long(juliancentury: float) -> float:
    """Calculate the sun's true longitude"""
    l0 = geom_mean_long_sun(juliancentury)
    c = sun_eq_of_center(juliancentury)

    return l0 + c


def sun_true_anomoly(juliancentury: float) -> float:
    """Calculate the sun's true anomaly"""
    m = geom_mean_anomaly_sun(juliancentury)
    c = sun_eq_of_center(juliancentury)

    return m + c


def sun_rad_vector(juliancentury: float) -> float:
    v = sun_true_anomoly(juliancentury)
    e = eccentric_location_earth_orbit(juliancentury)

    return (1.000001018 * (1 - e * e)) / (1 + e * cos(radians(v)))


def sun_apparent_long(juliancentury: float) -> float:
    true_long = sun_true_long(juliancentury)

    omega = 125.04 - 1934.136 * juliancentury
    return true_long - 0.00569 - 0.00478 * sin(radians(omega))


def mean_obliquity_of_ecliptic(juliancentury: float) -> float:
    seconds = 21.448 - juliancentury * (
        46.815 + juliancentury * (0.00059 - juliancentury * (0.001813))
    )
    return 23.0 + (26.0 + (seconds / 60.0)) / 60.0


def obliquity_correction(juliancentury: float) -> float:
    e0 = mean_obliquity_of_ecliptic(juliancentury)

    omega = 125.04 - 1934.136 * juliancentury
    return e0 + 0.00256 * cos(radians(omega))


def sun_rt_ascension(juliancentury: float) -> float:
    """Calculate the sun's right ascension"""
    oc = obliquity_correction(juliancentury)
    al = sun_apparent_long(juliancentury)

    tananum = cos(radians(oc)) * sin(radians(al))
    tanadenom = cos(radians(al))

    return degrees(atan2(tananum, tanadenom))


def sun_declination(juliancentury: float) -> float:
    """Calculate the sun's declination"""
    e = obliquity_correction(juliancentury)
    lambd = sun_apparent_long(juliancentury)

    sint = sin(radians(e)) * sin(radians(lambd))
    return degrees(asin(sint))


def var_y(juliancentury: float) -> float:
    epsilon = obliquity_correction(juliancentury)
    y = tan(radians(epsilon) / 2.0)
    return y * y


def eq_of_time(juliancentury: float) -> float:
    l0 = geom_mean_long_sun(juliancentury)
    e = eccentric_location_earth_orbit(juliancentury)
    m = geom_mean_anomaly_sun(juliancentury)

    y = var_y(juliancentury)

    sin2l0 = sin(2.0 * radians(l0))
    sinm = sin(radians(m))
    cos2l0 = cos(2.0 * radians(l0))
    sin4l0 = sin(4.0 * radians(l0))
    sin2m = sin(2.0 * radians(m))

    Etime = (
        y * sin2l0
        - 2.0 * e * sinm
        + 4.0 * e * y * sinm * cos2l0
        - 0.5 * y * y * sin4l0
        - 1.25 * e * e * sin2m
    )

    return degrees(Etime) * 4.0


def hour_angle(
    latitude: float, declination: float, zenith: float, direction: SunDirection
) -> float:
    """Calculate the hour angle of the sun

    See https://en.wikipedia.org/wiki/Hour_angle#Solar_hour_angle

    Args:
        latitude: The latitude of the obersver
        declination: The declination of the sun
        zenith: The zenith angle of the sun
        direction: The direction of traversal of the sun

    Raises:
        ValueError
    """

    latitude_rad = radians(latitude)
    declination_rad = radians(declination)
    zenith_rad = radians(zenith)

    # n = cos(zenith_rad)
    # d = cos(latitude_rad) * cos(declination_rad)
    # t = tan(latitude_rad) * tan(declination_rad)
    # h = (n / d) - t

    h = (cos(zenith_rad) - sin(latitude_rad) * sin(declination_rad)) / (
        cos(latitude_rad) * cos(declination_rad)
    )

    HA = acos(h)
    if direction == SunDirection.SETTING:
        HA = -HA
    return HA


def adjust_to_horizon(elevation: float) -> float:
    """Calculate the extra degrees of depression that you can see round the earth
    due to the increase in elevation.

    Args:
        elevation: Elevation above the earth in metres

    Returns:
        A number of degrees to add to adjust for the elevation of the observer
    """

    if elevation <= 0:
        return 0

    r = 6356900  # radius of the earth
    a1 = r
    h1 = r + elevation
    theta1 = acos(a1 / h1)
    return degrees(theta1)


def adjust_to_obscuring_feature(elevation: Tuple[float, float]) -> float:
    """Calculate the number of degrees to adjust for an obscuring feature"""
    if elevation[0] == 0.0:
        return 0.0

    sign = -1 if elevation[0] < 0.0 else 1
    return sign * degrees(
        acos(fabs(elevation[0]) / sqrt(pow(elevation[0], 2) + pow(elevation[1], 2)))
    )


def refraction_at_zenith(zenith: float) -> float:
    """Calculate the degrees of refraction of the sun due to the sun's elevation."""

    elevation = 90 - zenith
    if elevation >= 85.0:
        return 0

    refractionCorrection = 0.0
    te = tan(radians(elevation))
    if elevation > 5.0:
        refractionCorrection = (
            58.1 / te - 0.07 / (te * te * te) + 0.000086 / (te * te * te * te * te)
        )
    elif elevation > -0.575:
        step1 = -12.79 + elevation * 0.711
        step2 = 103.4 + elevation * step1
        step3 = -518.2 + elevation * step2
        refractionCorrection = 1735.0 + elevation * step3
    else:
        refractionCorrection = -20.774 / te

    refractionCorrection = refractionCorrection / 3600.0

    return refractionCorrection


def time_of_transit(
    observer: Observer, date: datetime.date, zenith: float, direction: SunDirection
) -> datetime.datetime:
    """Calculate the time in the UTC timezone when the sun transits the specificed zenith

    Args:
        observer: An observer viewing the sun at a specific, latitude, longitude and elevation
        date: The date to calculate for
        zenith: The zenith angle for which to calculate the transit time
        direction: The direction that the sun is traversing

    Raises:
        ValueError if the zenith is not transitted by the sun

    Returns:
        the time when the sun transits the specificed zenith
    """
    if observer.latitude > 89.8:
        latitude = 89.8
    elif observer.latitude < -89.8:
        latitude = -89.8
    else:
        latitude = observer.latitude

    adjustment_for_elevation = 0.0
    if isinstance(observer.elevation, float) and observer.elevation > 0.0:
        adjustment_for_elevation = adjust_to_horizon(observer.elevation)
    elif isinstance(observer.elevation, tuple):
        adjustment_for_elevation = adjust_to_obscuring_feature(observer.elevation)

    adjustment_for_refraction = refraction_at_zenith(zenith + adjustment_for_elevation)

    jd = julianday(date)
    t = jday_to_jcentury(jd)
    solarDec = sun_declination(t)

    hourangle = hour_angle(
        latitude,
        solarDec,
        zenith + adjustment_for_elevation - adjustment_for_refraction,
        direction,
    )

    delta = -observer.longitude - degrees(hourangle)
    timeDiff = 4.0 * delta
    timeUTC = 720.0 + timeDiff - eq_of_time(t)

    t = jday_to_jcentury(jcentury_to_jday(t) + timeUTC / 1440.0)
    solarDec = sun_declination(t)
    hourangle = hour_angle(
        latitude,
        solarDec,
        zenith + adjustment_for_elevation + adjustment_for_refraction,
        direction,
    )

    delta = -observer.longitude - degrees(hourangle)
    timeDiff = 4.0 * delta
    timeUTC = 720 + timeDiff - eq_of_time(t)

    td = minutes_to_timedelta(timeUTC)
    dt = datetime.datetime(date.year, date.month, date.day) + td
    dt = pytz.utc.localize(dt)  # pylint: disable=E1120
    return dt


def time_at_elevation(
    observer: Observer,
    elevation: float,
    date: Optional[datetime.date] = None,
    direction: SunDirection = SunDirection.RISING,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> datetime.datetime:
    """Calculates the time when the sun is at the specified elevation on the specified date.

    Note:
        This method uses positive elevations for those above the horizon.

        Elevations greater than 90 degrees are converted to a setting sun
        i.e. an elevation of 110 will calculate a setting sun at 70 degrees.

    Args:
        elevation: Elevation of the sun in degrees above the horizon to calculate for.
        observer:  Observer to calculate for
        date:      Date to calculate for. Default is today's date in the timezone `tzinfo`.
        direction: Determines whether the calculated time is for the sun rising or setting.
                   Use ``SunDirection.RISING`` or ``SunDirection.SETTING``. Default is rising.
        tzinfo:    Timezone to return times in. Default is UTC.

    Returns:
        Date and time at which the sun is at the specified elevation.
    """

    if elevation > 90.0:
        elevation = 180.0 - elevation
        direction = SunDirection.SETTING

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    zenith = 90 - elevation
    try:
        return time_of_transit(observer, date, zenith, direction).astimezone(tzinfo)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise ValueError(
                f"Sun never reaches an elevation of {elevation} degrees "
                "at this location."
            ) from exc
        else:
            raise


def noon(
    observer: Observer,
    date: Optional[datetime.date] = None,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> datetime.datetime:
    """Calculate solar noon time when the sun is at its highest point.

    Args:
        observer: An observer viewing the sun at a specific, latitude, longitude and elevation
        date:     Date to calculate for. Default is today for the specified tzinfo.
        tzinfo:   Timezone to return times in. Default is UTC.

    Returns:
        Date and time at which noon occurs.
    """
    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    jc = jday_to_jcentury(julianday(date))
    eqtime = eq_of_time(jc)
    timeUTC = (720.0 - (4 * observer.longitude) - eqtime) / 60.0

    hour = int(timeUTC)
    minute = int((timeUTC - hour) * 60)
    second = int((((timeUTC - hour) * 60) - minute) * 60)

    if second > 59:
        second -= 60
        minute += 1
    elif second < 0:
        second += 60
        minute -= 1

    if minute > 59:
        minute -= 60
        hour += 1
    elif minute < 0:
        minute += 60
        hour -= 1

    if hour > 23:
        hour -= 24
        date += datetime.timedelta(days=1)
    elif hour < 0:
        hour += 24
        date -= datetime.timedelta(days=1)

    noon = datetime.datetime(date.year, date.month, date.day, hour, minute, second)
    return pytz.utc.localize(noon).astimezone(tzinfo)  # pylint: disable=E1120


def midnight(
    observer: Observer,
    date: Optional[datetime.date] = None,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> datetime.datetime:
    """Calculate solar midnight time.

    Note:
        This calculates the solar midnight that is closest
        to 00:00:00 of the specified date i.e. it may return a time that is on
        the previous day.

    Args:
        observer: An observer viewing the sun at a specific, latitude, longitude and elevation
        date:     Date to calculate for. Default is today for the specified tzinfo.
        tzinfo:   Timezone to return times in. Default is UTC.

    Returns:
        Date and time at which midnight occurs.
    """
    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    jd = julianday(date)
    newt = jday_to_jcentury(jd + 0.5 + -observer.longitude / 360.0)

    eqtime = eq_of_time(newt)
    timeUTC = (-observer.longitude * 4.0) - eqtime

    timeUTC = timeUTC / 60.0
    hour = int(timeUTC)
    minute = int((timeUTC - hour) * 60)
    second = int((((timeUTC - hour) * 60) - minute) * 60)

    if second > 59:
        second -= 60
        minute += 1
    elif second < 0:
        second += 60
        minute -= 1

    if minute > 59:
        minute -= 60
        hour += 1
    elif minute < 0:
        minute += 60
        hour -= 1

    if hour < 0:
        hour += 24
        date -= datetime.timedelta(days=1)

    midnight = datetime.datetime(date.year, date.month, date.day, hour, minute, second)
    return pytz.utc.localize(midnight).astimezone(tzinfo)  # pylint: disable=E1120


def zenith_and_azimuth(
    observer: Observer, dateandtime: datetime.datetime, with_refraction: bool = True,
) -> Tuple[float, float]:
    if observer.latitude > 89.8:
        latitude = 89.8
    elif observer.latitude < -89.8:
        latitude = -89.8
    else:
        latitude = observer.latitude

    longitude = observer.longitude

    if dateandtime.tzinfo is None:
        zone = 0.0
        utc_datetime = dateandtime
    else:
        zone = -dateandtime.utcoffset().total_seconds() / 3600.0  # type: ignore
        utc_datetime = dateandtime.astimezone(pytz.utc)

    timenow = (
        utc_datetime.hour
        + (utc_datetime.minute / 60.0)
        + (utc_datetime.second / 3600.0)
    )

    JD = julianday(dateandtime)
    t = jday_to_jcentury(JD + timenow / 24.0)
    solarDec = sun_declination(t)
    eqtime = eq_of_time(t)

    solarTimeFix = eqtime - (4.0 * -longitude) + (60 * zone)
    trueSolarTime = (
        dateandtime.hour * 60.0
        + dateandtime.minute
        + dateandtime.second / 60.0
        + solarTimeFix
    )
    #    in minutes as a float, fractional part is seconds

    while trueSolarTime > 1440:
        trueSolarTime = trueSolarTime - 1440

    hourangle = trueSolarTime / 4.0 - 180.0
    #    Thanks to Louis Schwarzmayr for the next line:
    if hourangle < -180:
        hourangle = hourangle + 360.0

    harad = radians(hourangle)

    csz = sin(radians(latitude)) * sin(radians(solarDec)) + cos(
        radians(latitude)
    ) * cos(radians(solarDec)) * cos(harad)

    if csz > 1.0:
        csz = 1.0
    elif csz < -1.0:
        csz = -1.0

    zenith = degrees(acos(csz))

    azDenom = cos(radians(latitude)) * sin(radians(zenith))

    if abs(azDenom) > 0.001:
        azRad = (
            (sin(radians(latitude)) * cos(radians(zenith))) - sin(radians(solarDec))
        ) / azDenom

        if abs(azRad) > 1.0:
            if azRad < 0:
                azRad = -1.0
            else:
                azRad = 1.0

        azimuth = 180.0 - degrees(acos(azRad))

        if hourangle > 0.0:
            azimuth = -azimuth
    else:
        if latitude > 0.0:
            azimuth = 180.0
        else:
            azimuth = 0.0

    if azimuth < 0.0:
        azimuth = azimuth + 360.0

    if with_refraction:
        zenith -= refraction_at_zenith(zenith)

    return zenith, azimuth


def zenith(
    observer: Observer,
    dateandtime: Optional[datetime.datetime] = None,
    with_refraction: bool = True,
) -> float:
    """Calculate the zenith angle of the sun.

    Args:
        observer:    Observer to calculate the solar zenith for
        dateandtime: The date and time for which to calculate the angle.
                     If `dateandtime` is None or is a naive Python datetime
                     then it is assumed to be in the UTC timezone.
        with_refraction: If True adjust zenith to take refraction into account

    Returns:
        The zenith angle in degrees.
    """

    if dateandtime is None:
        dateandtime = now(pytz.UTC)

    return zenith_and_azimuth(observer, dateandtime, with_refraction)[0]


def azimuth(
    observer: Observer, dateandtime: Optional[datetime.datetime] = None,
) -> float:
    """Calculate the azimuth angle of the sun.

    Args:
        observer:    Observer to calculate the solar azimuth for
        dateandtime: The date and time for which to calculate the angle.
                     If `dateandtime` is None or is a naive Python datetime
                     then it is assumed to be in the UTC timezone.

    Returns:
        The azimuth angle in degrees clockwise from North.

    If `dateandtime` is a naive Python datetime then it is assumed to be
    in the UTC timezone.
    """

    if dateandtime is None:
        dateandtime = now(pytz.UTC)

    return zenith_and_azimuth(observer, dateandtime)[1]


def elevation(
    observer: Observer,
    dateandtime: Optional[datetime.datetime] = None,
    with_refraction: bool = True,
) -> float:
    """Calculate the sun's angle of elevation.

    Args:
        observer:    Observer to calculate the solar elevation for
        dateandtime: The date and time for which to calculate the angle.
                     If `dateandtime` is None or is a naive Python datetime
                     then it is assumed to be in the UTC timezone.
        with_refraction: If True adjust elevation to take refraction into account

    Returns:
        The elevation angle in degrees above the horizon.
    """

    if dateandtime is None:
        dateandtime = now(pytz.UTC)

    return 90.0 - zenith(observer, dateandtime, with_refraction)


def dawn(
    observer: Observer,
    date: Optional[datetime.date] = None,
    depression: Union[float, Depression] = Depression.CIVIL,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> datetime.datetime:
    """Calculate dawn time.

    Args:
        observer:   Observer to calculate dawn for
        date:       Date to calculate for. Default is today's date in the timezone `tzinfo`.
        depression: Number of degrees below the horizon to use to calculate dawn.
                    Default is for Civil dawn i.e. 6.0
        tzinfo:     Timezone to return times in. Default is UTC.

    Returns:
        Date and time at which dawn occurs.

    Raises:
        ValueError: if dawn does not occur on the specified date
    """
    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    dep: float = 0.0
    if isinstance(depression, Depression):
        dep = depression.value
    else:
        dep = depression

    try:
        return time_of_transit(
            observer, date, 90.0 + dep, SunDirection.RISING
        ).astimezone(tzinfo)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise ValueError(
                f"Sun never reaches {dep} degrees below the horizon, at this location."
            ) from exc
        else:
            raise


def sunrise(
    observer: Observer,
    date: Optional[datetime.date] = None,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> datetime.datetime:
    """Calculate sunrise time.

    Args:
        observer: Observer to calculate sunrise for
        date:     Date to calculate for. Default is today's date in the timezone `tzinfo`.
        tzinfo:   Timezone to return times in. Default is UTC.

    Returns:
        Date and time at which sunrise occurs.

    Raises:
        ValueError: if the sun does not reach the horizon on the specified date
    """
    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    try:
        return time_of_transit(
            observer, date, 90.0 + SUN_APPARENT_RADIUS, SunDirection.RISING,
        ).astimezone(tzinfo)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            z = zenith(observer, noon(observer, date))
            if z > 90.0:
                msg = "Sun is always below the horizon on this day, at this location."
            else:
                msg = "Sun is always above the horizon on this day, at this location."
            raise ValueError(msg) from exc
        else:
            raise


def sunset(
    observer: Observer,
    date: Optional[datetime.date] = None,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> datetime.datetime:
    """Calculate sunset time.

    Args:
        observer: Observer to calculate sunset for
        date:     Date to calculate for. Default is today's date in the timezone `tzinfo`.
        tzinfo:   Timezone to return times in. Default is UTC.

    Returns:
        Date and time at which sunset occurs.

    Raises:
        ValueError: if the sun does not reach the horizon
    """

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    try:
        return time_of_transit(
            observer, date, 90.0 + SUN_APPARENT_RADIUS, SunDirection.SETTING,
        ).astimezone(tzinfo)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            z = zenith(observer, noon(observer, date))
            if z > 90.0:
                msg = "Sun is always below the horizon on this day, at this location."
            else:
                msg = "Sun is always above the horizon on this day, at this location."
            raise ValueError(msg) from exc
        else:
            raise


def dusk(
    observer: Observer,
    date: Optional[datetime.date] = None,
    depression: Union[float, Depression] = Depression.CIVIL,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> datetime.datetime:
    """Calculate dusk time.

    Args:
        observer:   Observer to calculate dusk for
        date:       Date to calculate for. Default is today's date in the timezone `tzinfo`.
        depression: Number of degrees below the horizon to use to calculate dusk.
                    Default is for Civil dusk i.e. 6.0
        tzinfo:     Timezone to return times in. Default is UTC.

    Returns:
        Date and time at which dusk occurs.

    Raises:
        ValueError: if dusk does not occur on the specified date
    """

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    dep: float = 0.0
    if isinstance(depression, Depression):
        dep = depression.value
    else:
        dep = depression

    try:
        return time_of_transit(
            observer, date, 90.0 + dep, SunDirection.SETTING
        ).astimezone(tzinfo)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise ValueError(
                f"Sun never reaches {dep} degrees below the horizon, at this location."
            ) from exc
        else:
            raise


def daylight(
    observer: Observer,
    date: Optional[datetime.date] = None,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Calculate daylight start and end times.

    Args:
        observer: Observer to calculate daylight for
        date:     Date to calculate for. Default is today's date in the timezone `tzinfo`.
        tzinfo:   Timezone to return times in. Default is UTC.

    Returns:
        A tuple of the date and time at which daylight starts and ends.

    Raises:
        ValueError: if the sun does not rise or does not set
    """
    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    start = sunrise(observer, date, tzinfo)
    end = sunset(observer, date, tzinfo)

    return start, end


def night(
    observer: Observer,
    date: Optional[datetime.date] = None,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Calculate night start and end times.

    Night is calculated to be between astronomical dusk on the
    date specified and astronomical dawn of the next day.

    Args:
        observer: Observer to calculate night for
        date:     Date to calculate for. Default is today's date for the
                  specified tzinfo.
        tzinfo:   Timezone to return times in. Default is UTC.

    Returns:
        A tuple of the date and time at which night starts and ends.

    Raises:
        ValueError: if dawn does not occur on the specified date or
                    dusk on the following day
    """
    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    start = dusk(observer, date, 6, tzinfo)
    tomorrow = date + datetime.timedelta(days=1)
    end = dawn(observer, tomorrow, 6, tzinfo)

    return start, end


def twilight(
    observer: Observer,
    date: Optional[datetime.date] = None,
    direction: SunDirection = SunDirection.RISING,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Returns the start and end times of Twilight
    when the sun is traversing in the specified direction.

    This method defines twilight as being between the time
    when the sun is at -6 degrees and sunrise/sunset.

    Args:
        observer:  Observer to calculate twilight for
        date:      Date for which to calculate the times.
                      Default is today's date in the timezone `tzinfo`.
        direction: Determines whether the time is for the sun rising or setting.
                      Use ``astral.SunDirection.RISING`` or ``astral.SunDirection.SETTING``.
        tzinfo:    Timezone to return times in. Default is UTC.

    Returns:
        A tuple of the date and time at which twilight starts and ends.

    Raises:
        ValueError: if the sun does not rise or does not set
    """

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    start = time_of_transit(observer, date, 90 + 6, direction).astimezone(tzinfo)
    if direction == SunDirection.RISING:
        end = sunrise(observer, date, tzinfo).astimezone(tzinfo)
    else:
        end = sunset(observer, date, tzinfo).astimezone(tzinfo)

    if direction == SunDirection.RISING:
        return start, end
    else:
        return end, start


def golden_hour(
    observer: Observer,
    date: Optional[datetime.date] = None,
    direction: SunDirection = SunDirection.RISING,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Returns the start and end times of the Golden Hour
    when the sun is traversing in the specified direction.

    This method uses the definition from PhotoPills i.e. the
    golden hour is when the sun is between 4 degrees below the horizon
    and 6 degrees above.

    Args:
        observer:  Observer to calculate the golden hour for
        date:      Date for which to calculate the times.
                      Default is today's date in the timezone `tzinfo`.
        direction: Determines whether the time is for the sun rising or setting.
                      Use ``SunDirection.RISING`` or ``SunDirection.SETTING``.
        tzinfo:    Timezone to return times in. Default is UTC.

    Returns:
        A tuple of the date and time at which the Golden Hour starts and ends.

    Raises:
        ValueError: if the sun does not transit the elevations -4 & +6 degrees
    """

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    start = time_of_transit(observer, date, 90 + 4, direction).astimezone(tzinfo)
    end = time_of_transit(observer, date, 90 - 6, direction).astimezone(tzinfo)

    if direction == SunDirection.RISING:
        return start, end
    else:
        return end, start


def blue_hour(
    observer: Observer,
    date: Optional[datetime.date] = None,
    direction: SunDirection = SunDirection.RISING,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Returns the start and end times of the Blue Hour
    when the sun is traversing in the specified direction.

    This method uses the definition from PhotoPills i.e. the
    blue hour is when the sun is between 6 and 4 degrees below the horizon.

    Args:
        observer:  Observer to calculate the blue hour for
        date:      Date for which to calculate the times.
                      Default is today's date in the timezone `tzinfo`.
        direction: Determines whether the time is for the sun rising or setting.
                      Use ``SunDirection.RISING`` or ``SunDirection.SETTING``.
        tzinfo:    Timezone to return times in. Default is UTC.

    Returns:
        A tuple of the date and time at which the Blue Hour starts and ends.

    Raises:
        ValueError: if the sun does not transit the elevations -4 & -6 degrees
    """

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    start = time_of_transit(observer, date, 90 + 6, direction).astimezone(tzinfo)
    end = time_of_transit(observer, date, 90 + 4, direction).astimezone(tzinfo)

    if direction == SunDirection.RISING:
        return start, end
    else:
        return end, start


def rahukaalam(
    observer: Observer,
    date: Optional[datetime.date] = None,
    daytime: bool = True,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Calculate ruhakaalam times.

    Args:
        observer: Observer to calculate rahukaalam for
        date:     Date to calculate for. Default is today's date in the timezone `tzinfo`.
        daytime:  If True calculate for the day time else calculate for the night time.
        tzinfo:   Timezone to return times in. Default is UTC.

    Returns:
        Tuple containing the start and end times for Rahukaalam.

    Raises:
        ValueError: if the sun does not rise or does not set
    """

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    if daytime:
        start = sunrise(observer, date, tzinfo)
        end = sunset(observer, date, tzinfo)
    else:
        start = sunset(observer, date, tzinfo)
        oneday = datetime.timedelta(days=1)
        end = sunrise(observer, date + oneday, tzinfo)

    octant_duration = datetime.timedelta(seconds=(end - start).seconds / 8)

    # Mo,Sa,Fr,We,Th,Tu,Su
    octant_index = [1, 6, 4, 5, 3, 2, 7]

    weekday = date.weekday()
    octant = octant_index[weekday]

    start = start + (octant_duration * octant)
    end = start + octant_duration

    return start, end


def sun(
    observer: Observer,
    date: Optional[datetime.date] = None,
    dawn_dusk_depression: Union[float, Depression] = Depression.CIVIL,
    tzinfo: Union[str, datetime.tzinfo] = pytz.utc,
) -> Dict:
    """Calculate all the info for the sun at once.

    Args:
        observer:             Observer for which to calculate the times of the sun
        date:                 Date to calculate for.
                              Default is today's date in the timezone `tzinfo`.
        dawn_dusk_depression: Depression to use to calculate dawn and dusk.
                              Default is for Civil dusk i.e. 6.0
        tzinfo:               Timezone to return times in. Default is UTC.

    Returns:
        Dictionary with keys ``dawn``, ``sunrise``, ``noon``, ``sunset`` and ``dusk``
        whose values are the results of the corresponding functions.

    Raises:
        ValueError: if passed through from any of the functions
    """

    if isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if date is None:
        date = today(tzinfo)

    return {
        "dawn": dawn(observer, date, dawn_dusk_depression, tzinfo),
        "sunrise": sunrise(observer, date, tzinfo),
        "noon": noon(observer, date, tzinfo),
        "sunset": sunset(observer, date, tzinfo),
        "dusk": dusk(observer, date, dawn_dusk_depression, tzinfo),
    }
