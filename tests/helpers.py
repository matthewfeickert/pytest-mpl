from pathlib import Path


def pytester_path(pytester):
    if hasattr(pytester, "path"):
        return pytester.path
    return Path(pytester.tmp_path)  # pytest v5
