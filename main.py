import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Add this dummy server so Koyeb stays happy
def run_dummy_server():
    server_address = ('', int(os.getenv("PORT", 8080)))
    httpd = HTTPServer(server_address, BaseHTTPRequestHandler)
    httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
