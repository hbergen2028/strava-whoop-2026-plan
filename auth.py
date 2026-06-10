"""
Strava OAuth2 authentication.
Opens your browser, captures the callback on localhost:8080, exchanges for tokens,
and saves them to .env.

Usage: python auth.py
"""

import os
import sys
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

import requests
from dotenv import load_dotenv, set_key

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_FILE)

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8080/callback")

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful! You can close this tab.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization failed.</h1>")

    def log_message(self, format, *args):
        pass  # suppress server logs


def main():
    if not CLIENT_ID or CLIENT_ID == "your_client_id_here":
        print("ERROR: Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env first.")
        sys.exit(1)

    # Start local callback server
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()

    # Build authorization URL
    auth_url = "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "force",
        "scope": "activity:read_all",
    })

    print("Opening browser for Strava authorization...")
    print(f"If it doesn't open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    thread.join(timeout=120)

    if not auth_code:
        print("ERROR: No authorization code received (120s timeout).")
        sys.exit(1)

    # Exchange code for tokens
    print("Exchanging code for tokens...")
    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    data = resp.json()

    set_key(ENV_FILE, "STRAVA_ACCESS_TOKEN", data["access_token"])
    set_key(ENV_FILE, "STRAVA_REFRESH_TOKEN", data["refresh_token"])
    set_key(ENV_FILE, "STRAVA_TOKEN_EXPIRES_AT", str(data["expires_at"]))

    athlete = data.get("athlete", {})
    print(f"\nAuthenticated as: {athlete.get('firstname', '')} {athlete.get('lastname', '')}")
    print("Tokens saved to .env — run fetch.py next.")


if __name__ == "__main__":
    main()
