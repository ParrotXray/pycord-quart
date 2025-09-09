"""
pycord-quart Discord OAuth2 Authentication Module
"""

import logging
import secrets
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import aiohttp
from quart import jsonify, redirect, request, session

from .exceptions import DiscordAuthError, TokenExchangeError, UserInfoError
from .status import ResponseData, ResponseStatus

logger = logging.getLogger(__name__)


class DiscordAuth:
    """Discord OAuth2 Authentication Handler"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        prompt: str = None,
        scopes: List[str] = None,
    ):
        """
        Initialize Discord authentication handler

        Args:
            client_id: Discord application ID
            client_secret: Discord application secret
            redirect_uri: OAuth2 redirect URI
            prompt: OAuth2 prompt parameter ('consent', 'none', or None for default)
            scopes: OAuth2 authorization scopes
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.prompt = prompt
        self.scopes = scopes or ["identify", "email", "guilds"]
        self.DISCORD_API_BASE = "https://discord.com/api/v10"
        self.DISCORD_OAUTH_BASE = "https://discord.com/api/oauth2"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access token

        Args:
            code: OAuth2 authorization code

        Returns:
            Token data dictionary

        Raises:
            TokenExchangeError: If token exchange fails
        """

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        encoded_data = urlencode(data)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.DISCORD_OAUTH_BASE}/token", data=encoded_data, headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        raise TokenExchangeError(
                            f"Token exchange failed: {response.status} - {text}"
                        )
        except aiohttp.ClientError as e:
            raise TokenExchangeError(f"Network error during token exchange: {e}")

    async def get_user_info(self, access_token: str) -> Dict:
        """
        Get user information

        Args:
            access_token: Access token

        Returns:
            User information dictionary

        Raises:
            UserInfoError: If user info retrieval fails
        """
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.DISCORD_API_BASE}/users/@me", headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        raise UserInfoError(f"Failed to get user info: {response.status} - {text}")
        except aiohttp.ClientError as e:
            raise UserInfoError(f"Network error during user info retrieval: {e}")

    async def get_user_guilds(self, access_token: str) -> List[Dict]:
        """
        Get user guild list

        Args:
            access_token: Access token

        Returns:
            User guild list

        Raises:
            UserInfoError: If guild list retrieval fails
        """
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.DISCORD_API_BASE}/users/@me/guilds", headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        raise UserInfoError(f"Failed to get guilds: {response.status} - {text}")
        except aiohttp.ClientError as e:
            raise UserInfoError(f"Network error during guilds retrieval: {e}")

    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke access token

        Args:
            access_token: Access token to revoke

        Returns:
            Whether revocation was successful
        """
        from urllib.parse import urlencode

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "token": access_token,
        }

        encoded_data = urlencode(data)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.DISCORD_OAUTH_BASE}/token/revoke", data=encoded_data, headers=headers
                ) as response:
                    return response.status == 200
        except aiohttp.ClientError as e:
            logger.warning(f"Token revocation failed: {e}")
            return False

    def generate_login_url(self, state: str = None) -> str:
        """
        Generate Discord OAuth2 login URL

        Args:
            state: Security state parameter, auto-generated if None

        Returns:
            Login URL
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "prompt": self.prompt,
        }

        return f"{self.DISCORD_OAUTH_BASE}/authorize?{urlencode(params)}"

    def get_avatar_url(self, user_data: Dict) -> str:
        """
        Build user avatar URL

        Args:
            user_data: User data dictionary

        Returns:
            Avatar URL
        """
        if user_data.get("avatar"):
            return f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png"
        else:
            # Use default avatar
            discriminator = int(user_data.get("discriminator", 0))
            return f"https://cdn.discordapp.com/embed/avatars/{discriminator % 5}.png"

    def process_user_data(self, user_data: Dict) -> Dict:
        """
        Process user data, add avatar URL and other info

        Args:
            user_data: Raw user data

        Returns:
            Processed user data
        """
        processed_data = {
            "id": str(user_data["id"]),
            "username": user_data["username"],
            "discriminator": user_data.get("discriminator", "0000"),
            "avatar": self.get_avatar_url(user_data),
            "email": user_data.get("email"),
        }
        return processed_data

    def filter_admin_guilds(self, guilds: List[Dict], guild_ids: List[int] = None) -> List[Dict]:
        """
        Filter guilds where user has administrator permissions

        Args:
            guilds: Guild list
            guild_ids: List of guild IDs where bot is present

        Returns:
            List of guilds with administrator permissions
        """
        admin_guilds = []
        for guild_data in guilds:
            permissions = int(guild_data.get("permissions", 0))
            if permissions & 8:
                guild_info = {
                    "id": guild_data["id"],
                    "name": guild_data["name"],
                    "icon": (
                        f"https://cdn.discordapp.com/icons/{guild_data['id']}/{guild_data['icon']}.png"
                        if guild_data.get("icon")
                        else None
                    ),
                    "owner": guild_data.get("owner", False),
                    "permissions": str(permissions),
                    "bot_present": int(guild_data["id"]) in guild_ids,
                }
                admin_guilds.append(guild_info)
        return admin_guilds

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated

        Returns:
            Authentication status
        """
        return (
            session.get("authenticated")
            and session.get("user_info")
            and session.get("access_token")
        )

    def get_user_info_from_session(self) -> Optional[Dict]:
        """
        Get user info from session

        Returns:
            User info or None
        """
        if self.is_authenticated():
            return session.get("user_info")
        return None

    def get_access_token_from_session(self) -> Optional[str]:
        """
        Get access token from session

        Returns:
            Access token or None
        """
        if self.is_authenticated():
            return session.get("access_token")
        return None

    async def login_handler(self):
        """
        Login request route handler

        Returns:
            JSON response
        """
        try:
            # Generate random state parameter for security
            state = secrets.token_urlsafe(32)
            session["oauth_state"] = state
            session.permanent = True

            login_url = self.generate_login_url(state)

            logger.debug(f"Generated login URL: {login_url}")

            return ResponseStatus(code=200, success=True, data=ResponseData(login_url=login_url))

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return ResponseStatus(code=500, success=False, error=str(e))

    async def callback_handler(self):
        """
        OAuth2 callback route handler

        Returns:
            Redirect response
        """
        try:
            logger.debug(f"Received callback request: {request.args}")

            # Check required parameters
            code = request.args.get("code")
            state = request.args.get("state")
            error = request.args.get("error")

            if error:
                logger.error(f"OAuth error: {error}")

                return ResponseStatus(code=500, success=False, error=f"OAuth error: {error}")

            if not code:
                logger.error("Missing code parameter in callback")

                return ResponseStatus(code=400, success=False, error="Missing authorization code")

            if not state:
                logger.error("Missing state parameter in callback")

                return ResponseStatus(code=500, success=False, error="Missing state parameter")

            stored_state = session.get("oauth_state")
            if stored_state and state != stored_state:
                logger.error("State parameter mismatch")

                return ResponseStatus(
                    code=400, success=False, error="Invalid state parameter - possible CSRF attack"
                )

            token_data = await self.exchange_code_for_token(code)
            access_token = token_data["access_token"]

            user_data = await self.get_user_info(access_token)
            processed_user_data = self.process_user_data(user_data)

            session["user_info"] = processed_user_data
            session["access_token"] = access_token
            session["token_data"] = token_data
            session["authenticated"] = True
            session.permanent = True

            session.pop("oauth_state", None)

            logger.debug("Authentication successful")

            return ResponseStatus(
                code=200, success=True, data=ResponseData(user=processed_user_data)
            )

        except Exception as e:
            logger.error(f"Callback processing failed: {e}")

            return ResponseStatus(code=500, success=False, error=str(e))

    async def status_handler(self):
        """
        Authentication status check route handler

        Returns:
            JSON response
        """
        try:
            if self.is_authenticated():
                return ResponseStatus(
                    code=200,
                    success=True,
                    data=ResponseData(authenticated=True, user=self.get_user_info_from_session()),
                )

            else:
                return ResponseStatus(
                    code=200, success=True, data=ResponseData(authenticated=False)
                )

        except Exception as e:
            logger.error(f"Authentication status check failed: {e}")
            return ResponseStatus(code=500, success=False, error=str(e))

    async def logout_handler(self):
        """
        Logout request route handler

        Returns:
            JSON response
        """
        try:
            if self.prompt != "none":
                access_token = session.get("access_token")
                if access_token:
                    await self.revoke_token(access_token)

            session.clear()

            return ResponseStatus(code=200, success=True, message="Successfully logged out")

        except Exception as e:
            logger.error(f"Logout failed: {e}")

            return ResponseStatus(code=500, success=False, error=str(e))

    async def guilds_handler(self, guild_ids: List[int], sort: bool = True) -> ResponseStatus:
        """
        Get user guilds route handler

        Args:
            guild_ids: List of guild IDs where bot is present
            sort: Whether to sort guilds by bot presence (default: True)

        Returns:
            ResponseStatus object
        """
        try:
            if not self.is_authenticated():
                return ResponseStatus(code=401, success=False, error="Unauthorized")

            access_token = self.get_access_token_from_session()
            user_guilds_data = await self.get_user_guilds(access_token)

            admin_guilds = self.filter_admin_guilds(user_guilds_data, guild_ids)

            if sort:
                admin_guilds.sort(key=lambda x: not x["bot_present"])

            return ResponseStatus(
                code=200,
                success=True,
                data=ResponseData(guilds=admin_guilds, total_count=len(admin_guilds)),
            )

        except Exception as e:
            logger.error(f"Failed to get guilds: {e}")
            return ResponseStatus(code=500, success=False, error=str(e))

    def get_bot_invite_url(
        self, client_id: str, guild_id: Optional[str] = None, permissions: int = 8
    ) -> str:
        """
        Generate bot invite URL

        Args:
            client_id: Discord application ID
            guild_id: Guild ID (optional)
            permissions: Permission value (default is administrator)

        Returns:
            Invite URL
        """
        base_url = "https://discord.com/oauth2/authorize"
        params = [
            f"client_id={client_id}",
            "scope=bot",
            f"permissions={permissions}",
            "response_type=code",
        ]

        if guild_id:
            params.append(f"guild_id={guild_id}")

        return f"{base_url}?{'&'.join(params)}"
