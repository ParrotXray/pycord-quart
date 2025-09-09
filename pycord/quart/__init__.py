"""
pycord-quart - Discord OAuth2 authentication library for Quart applications
"""

from typing import NamedTuple

from .auth import DiscordAuth
from .decorators import get_access_token, get_current_user, require_auth
from .exceptions import DiscordAuthError, TokenExchangeError, UserInfoError
from .status import ResponseData, ResponseStatus


class _VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    release: str
    serial: int


__version__ = "0.1.4"
__version_info__ = _VersionInfo(0, 1, 4, "final", 0)

version = __version__
version_info = __version_info__

__all__ = [
    "DiscordAuth",
    "require_auth",
    "get_current_user",
    "get_access_token",
    "DiscordAuthError",
    "TokenExchangeError",
    "UserInfoError",
    "ResponseStatus",
    "ResponseData" "__version__",
    "__version_info__",
]
