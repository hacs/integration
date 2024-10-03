"""Library constants."""

from typing import Final

# APIs
API_INFO: Final = "SYNO.API.Info"
API_AUTH: Final = "SYNO.API.Auth"

# Parameters to be masked on debug output
SENSITIV_PARAMS: Final = ["account", "passwd", "_sid", "SynoToken", "device_id"]

# SYNO.*
ERROR_COMMON: Final = {
    100: "Unknown error",
    101: "No parameter API, method, or version",
    102: "API does not exist",
    103: "API method does not exist",
    104: "API version not supported",
    105: "Insufficient user privilege",
    106: "Session timeout",
    107: "Session interrupted by duplicate login",
    114: "Missing required parameters",
    117: "Unknown internal error",
    120: "Invalid parameter",
    160: "Insufficient application privilege",
}

# SYNO.API.Auth
ERROR_AUTH: Final = {
    400: "Invalid credentials",
    401: "Guest or disabled account",
    402: "Permission denied",
    403: "One time password not specified",
    404: "One time password authenticate failed",
    405: "App portal incorrect",
    406: "One time password code enforced",
    407: "Max Tries (if auto blocking is set to true)",
    408: "Password Expired Can not Change",
    409: "Password Expired",
    410: "Password must change (when first time use or after reset password by admin)",
    411: "Account Locked (when account max try exceed)",
}

# SYNO.DownloadStation[2].BTSearch
ERROR_DOWNLOAD_SEARCH: Final = {
    400: "Unknown error",
    401: "Invalid parameter",
    402: "Parse the user setting failed",
    403: "Get category failed",
    404: "Get the search result from DB failed",
    405: "Get the user setting failed",
}
# SYNO.DownloadStation[2].Task
ERROR_DOWNLOAD_TASK: Final = {
    400: "File upload failed",
    401: "Max number of tasks reached",
    402: "Destination denied",
    403: "Destination does not exist",
    404: "Invalid task id",
    405: "Invalid task action",
    406: "No default destination",
    407: "Set destination failed",
    408: "File does not exist",
}

# SYNO.FileStation.*
ERROR_FILE: Final = {
    400: "Invalid parameter of file operation",
    401: "Unknown error of file operation",
    402: "System is too busy",
    403: "Invalid user does this file operation",
    404: "Invalid group does this file operation",
    405: "Invalid user and group does this file operation",
    406: "Can’t get user/group information from the account server Operation not permitted",
    407: "Operation not permitted",
    408: "No such file or directory",
    409: "Non-supported file system",
    410: "Failed to connect internet-based file system (ex: CIFS)",
    411: "Read-only file system",
    412: "Filename too long in the non-encrypted file system",
    413: "Filename too long in the encrypted file system",
    414: "File already exists",
    415: "Disk quota exceeded",
    416: "No space left on device",
    417: "Input/output error",
    418: "Illegal name or path",
    419: "Illegal file name",
    420: "Illegal file name on FAT file system",
    421: "Device or resource busy",
    599: "No such task of the file operation",
    900: "Failed to delete file(s)/folder(s). More information in <errors> object",
    1000: "Failed to copy files/folders. More information in <errors> object",
    1001: "Failed to move files/folders. More information in <errors> object",
    1002: "An error occurred at the destination. More information in <errors> object",
    1003: "Cannot overwrite or skip the existing file because no overwrite parameter is given",
    1004: "File cannot overwrite a folder with the same name, or folder cannot overwrite a file with the same name",  # pylint: disable=line-too-long
    1006: "Cannot copy/move file/folder with special characters to a FAT32 file system",
    1007: "Cannot copy/move a file bigger than 4G to a FAT32 file system",
    1100: "Failed to create a folder. More information in <errors> object",
    1101: "The number of folders to the parent folder would exceed the system limitation",
    1300: "Failed to compress files/folders",
    1301: "Cannot create the archive because the given archive name is too long",
    1400: "Failed to extract files",
    1401: "Cannot open the file as archive",
    1402: "Failed to read archive data error",
    1403: "Wrong archive password",
    1404: "Failed to get the file and dir list in an archive",
    1405: "Failed to find the item ID in an archive file",
    1200: "Failed to rename it. More information in <errors> object",
    1800: "There is no Content-Length information in the HTTP header or the received size doesn’t match the value of Content-Length information in the HTTP header",  # pylint: disable=line-too-long
    1801: "Wait too long, no date can be received from client (Default maximum wait time is 3600 seconds)",  # pylint: disable=line-too-long
    1802: "No filename information in the last part of file content",
    1803: "Upload connection is cancelled",
    1804: "Failed to upload too big file to FAT file system",
    1805: "Can’t overwrite or skip the existed file, if no overwrite parameter is given",
    2000: "Sharing link does not exist",
    2001: "Cannot generate sharing link because too many sharing links exist",
    2002: "Failed to access sharing links",
}

# SYNO.SurveillanceStation.*
ERROR_SURVEILLANCE: Final = {
    400: "Execution failed",
    401: "Invalid parameter",
    402: "Camera disabled",
    403: "Insufficient license",
    404: "Codec activation failed",
    405: "CMS server connection failed",
    407: "CMS closed",
    412: "Need to add license",
    413: "Reach the maximum of platform",
    414: "Some events not exist",
    415: "Message connect failed",
    417: "Test connection error",
    418: "Object/VisualStation ID does not exist",
    419: "VisualStation name repetition",
    439: "Too many items selected",
    446: "Task path already exist",
    522: "Original task is migrating",
    534: "Exceed name length limitation",
}

# SYNO.Virtualization.*
ERROR_VIRTUALIZATION: Final = {
    400: "Unknown error",
    401: "Bad parameter",
    402: "Operation failed",
    403: "Name conflict",
    404: "The number of iSCSI LUNs has reached the system limit",
    500: "Note: vdisk is based on iSCSI LUN, which is also limited by the system",
    501: "The cluster is frozen. More than half of the hosts are offline",
    600: "The cluster is in the incompatible mode. Please upgrade to a compatible DSM version and try again",  # pylint: disable=line-too-long
    601: "The cluster is not ready",
    700: "The host is offline",
    900: "The storage is in invalid",
    901: "Failed to set a host to a virtual machine",
    902: "The virtual machine does not have a host",
    903: "Failed to power on a virtual machine due to insufficient CPU threads",
    904: "Failed to power on a virtual machine due to insufficient memory",
    905: "The status of virtual machine is online",
    906: "MAC conflict",
    907: "Failed to create virtual machine because the selected image is not found",
    908: "The status of virtual machine is offline",
    909: "Failed to power on a virtual machine due to insufficient CPU threads for reservation on the host",  # pylint: disable=line-too-long
    910: "Failed to power on the virtual machine because there is no corresponding networking on the host",  # pylint: disable=line-too-long
    911: "Only the VirtIO hard disk controller can be used to boot the virtual machine remotely. Virtual machines with UEFI enabled cannot be powered on remotely",  # pylint: disable=line-too-long
    1000: "Cannot find task_id",
    1001: "Need Virtual Machine Manager Pro",
    1400: "The result of image creating is partial success",
    1600: "The virtual machine has been successfully edited. However, errors occurred while reserving the memory or CPU on the HA hosts",  # pylint: disable=line-too-long
}
