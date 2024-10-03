"""Synology SurveillanceStation API constants."""

RECORDING_STATUS = [
    1,  # Continue recording schedule
    2,  # Motion detect recording schedule
    3,  # Digital input recording schedule
    4,  # Digital input recording schedule
    5,  # Manual recording schedule
]
MOTION_DETECTION_DISABLED = -1
MOTION_DETECTION_BY_CAMERA = 0
MOTION_DETECTION_BY_SURVEILLANCE = 1

SNAPSHOT_SIZE_ICON = 1
SNAPSHOT_SIZE_FULL = 2

SNAPSHOT_PROFILE_HIGH_QUALITY = 0
SNAPSHOT_PROFILE_BALANCED = 1
SNAPSHOT_PROFILE_LOW_BANDWIDTH = 2
