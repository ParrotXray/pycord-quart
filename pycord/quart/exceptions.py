"""
pycord-quart Exception Classes
"""


class DiscordAuthError(Exception):
    """Base Discord authentication exception"""

    pass


class TokenExchangeError(DiscordAuthError):
    """Token exchange failure exception"""

    pass


class UserInfoError(DiscordAuthError):
    """User information retrieval failure exception"""

    pass
