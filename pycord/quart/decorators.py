"""
pycord-quart Decorators
"""

from functools import wraps

from quart import jsonify, session

from .status import ResponseData, ResponseStatus


def require_auth(f):
    """
    Authentication decorator
    Used to protect routes that require authentication

    Usage:
        @app.route("/protected")
        @require_auth
        async def protected_route():
            return "This is protected"
    """

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if not (
            session.get("authenticated")
            and session.get("user_info")
            and session.get("access_token")
        ):
            return ResponseStatus(code=401, success=False, error="Unauthorized")
        return await f(*args, **kwargs)

    return decorated_function


def get_current_user():
    """
    Get current authenticated user information

    Returns:
        User info dictionary or None
    """
    if session.get("authenticated") and session.get("user_info") and session.get("access_token"):
        return session.get("user_info")
    return None


def get_access_token():
    """
    Get current user access token

    Returns:
        Access token or None
    """
    if session.get("authenticated") and session.get("user_info") and session.get("access_token"):
        return session.get("access_token")
    return None
