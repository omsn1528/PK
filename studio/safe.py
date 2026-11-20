"""Small helpers for what is safe to show a user."""
import re

_PATH = re.compile(r"(?:[A-Za-z]:)?[\\/][^\s'\"]*[\\/][^\s'\"]+")


def friendly(e, limit=600) -> str:
    """An error message for the user: trimmed, with any server file paths removed. A missing ffmpeg, which Windows
    reports only as "the system cannot find the file specified", is said in plain words with what to do."""
    from . import tools
    s = str(e)
    if "DECRYPTION_FAILED_OR_BAD_RECORD_MAC" in s:
        return "Network connection dropped or TLS data packet corrupted during download. Check your internet/VPN connection and retry."
    return tools.explain(e) or _PATH.sub("[file]", s[-limit:])

