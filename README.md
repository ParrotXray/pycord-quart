# pycord-quart
A pycord extension for Discord OAuth2 authentication in Quart applications.

# Installation 
Python >= 3.10.x is required.
```bash=
# Windows
pip install --upgrade pycord-quart

# Linux
pip3 install --upgrade pycord-quart
```
# Examples
```py= 
from quart import Quart, request, session, redirect, url_for, jsonify
from pycord.ipc import Client
from pycord.quart import DiscordAuth, require_auth, get_current_user

app = Quart(__name__)
ipc_client = Client(secret_key=<"your IPCSecret">, host=<"your IPC Server IP">, port=<"your IPC Server Port">)

app.config["SECRET_KEY"] = <"your SecretKey">

discord_auth = DiscordAuth(
    client_id=<"your DiscordClientID">,
    client_secret=<"your DiscordClientSecret">,
    redirect_uri=<"your DiscordRedirectURI">,
    scopes=['identify', 'email', 'guilds'],
)

@app.route("/api/auth/login", methods=["GET"])
async def api_login():
    response = await discord_auth.login_handler()
    
    return jsonify(response.to_json), response.code

@app.route("/api/auth/callback", methods=["GET"])
async def api_callback():
    response = await discord_auth.callback_handler()

    return jsonify(response.to_json), response.code

@app.route("/api/auth/logout", methods=["POST"])
async def api_logout():
    response = await discord_auth.logout_handler()

    return jsonify(response.to_json), response.code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
```