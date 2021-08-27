"""Filter functions."""


def filter_content_return_one_of_type(content, namestartswith, filterfiltype, attr="name"):
    """Only match 1 of the filter."""
    contents = []
    filetypefound = False
    for filename in content:
        if isinstance(filename, str):
            if filename.startswith(namestartswith):
                if filename.endswith(f".{filterfiltype}"):
                    if not filetypefound:
                        contents.append(filename)
                        filetypefound = True
                    continue
                else:
                    contents.append(filename)
        else:
            if getattr(filename, attr).startswith(namestartswith):
                if getattr(filename, attr).endswith(f".{filterfiltype}"):
                    if not filetypefound:
                        contents.append(filename)
                        filetypefound = True
                    continue
                else:
                    contents.append(filename)
    return contents


def find_first_of_filetype(content, filterfiltype, attr="name"):
    """Find the first of the file type."""
    filename = ""
    for _filename in content:
        if isinstance(_filename, str):
            if _filename.endswith(f".{filterfiltype}"):
                filename = _filename
                break
        else:
            if getattr(_filename, attr).endswith(f".{filterfiltype}"):
                filename = getattr(_filename, attr)
                break
    return filename


def get_first_directory_in_directory(content, dirname):
    """Return the first directory in dirname or None."""
    directory = None
    for path in content:
        if path.full_path.startswith(dirname) and path.full_path != dirname:
            if path.is_directory:
                directory = path.filename
                break
    return directory
