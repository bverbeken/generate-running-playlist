#! /usr/bin/env python

import http.server
import socketserver
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

from spotipy.oauth2 import SpotifyOAuth

from spotify_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_PORT

PORT = SPOTIFY_REDIRECT_PORT

# This will hold the authorization code when it's received
auth_code = None

auth_manager = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=f"http://localhost:{SPOTIFY_REDIRECT_PORT}",
    scope='playlist-modify-public playlist-modify-private',
    open_browser=False
)


def start_callback_server():
    class SpotifyAuthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            global auth_code
            url = urlparse(self.path)
            query_params = parse_qs(url.query)

            if 'code' in query_params:
                auth_code = query_params['code'][0]
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authentication successful! You can close this window.")
            else:
                # If 'code' parameter is not present, send an error message
                self.send_response(400)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authentication failed: 'code' parameter not found in the query string.")
            threading.Thread(target=httpd.shutdown, daemon=True).start()

    # Create and start the HTTP server
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SpotifyAuthHandler) as httpd:
        httpd.serve_forever()


def wait_for_http_server_shutdown():
    import socket
    import time
    timeout = 300.0
    start_time = time.time()
    while True:
        # Attempt to connect to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', PORT))
                # If bind is successful, break from the loop
                break
            except socket.error as e:
                time.sleep(0.5)  # Wait a bit before trying again
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Timed out waiting for port {PORT} to become free.") from e


def get_token():
    auth_url = auth_manager.get_authorize_url()
    webbrowser.open(auth_url)

    start_callback_server()
    wait_for_http_server_shutdown()

    if auth_code:
        return auth_manager.get_access_token(auth_code, as_dict=False)
        # Now you can create your Spotify client with the access token
        # spotify = spotipy.Spotify(auth=token_info['access_token'])
        # ... and continue with your application logic
    else:
        # TODO error handling
        print("Failed to retrieve authentication code.")


token = get_token()
print(token)
