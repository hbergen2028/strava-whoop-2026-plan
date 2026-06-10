"""
WHOOP OAuth2 authentication.
Opens your browser, captures the callback on localhost:8081, exchanges for tokens,
and saves them to .env.

Usage: python whoop_auth.py
"""

import os
import sys
import time
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

import requests
from dotenv import load_dotenv, set_key

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE)

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI", "http://localhost:8081/callback")

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
SCOPES = "read:recovery read:cycles read:sleep read:workout read:profile offline"

auth_code = None
returned_state = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code, returned_state
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            returned_state = params.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>WHOOP authorization successful! You can close this tab.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization failed.</h1>")

    def log_message(self, format, *args):
        pass  # suppress server logs


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: Set WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET in .env first.")
        sys.exit(1)

    port = urllib.parse.urlparse(REDIRECT_URI).port or 8081
    server = HTTPServer(("localhost", port), CallbackHandler)
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()

    state = secrets.token_urlsafe(12)
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    })

    print("Opening browser for WHOOP authorization...")
    print(f"If it doesn't open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    thread.join(timeout=180)

    if not auth_code:
        print("ERROR: No authorization code received (180s timeout).")
        sys.exit(1)

    if returned_state != state:
        print("ERROR: state mismatch — possible CSRF, aborting.")
        sys.exit(1)

    print("Exchanging code for tokens...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    })
    resp.raise_for_status()
    data = resp.json()

    expires_at = int(time.time()) + int(data.get("expires_in", 3600))
    set_key(ENV_FILE, "WHOOP_ACCESS_TOKEN", data["access_token"])
    set_key(ENV_FILE, "WHOOP_REFRESH_TOKEN", data.get("refresh_token", ""))
    set_key(ENV_FILE, "WHOOP_TOKEN_EXPIRES_AT", str(expires_at))

    print("\nWHOOP tokens saved to .env.")


if __name__ == "__main__":
    main()
