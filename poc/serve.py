"""Dev server.

Auto-uses HTTPS when cert.pem + key.pem exist (Stage 2 needs HTTPS for
the phone's camera permission). Falls back to plain HTTP otherwise
(Stage 0 audio-only test works fine on HTTP from localhost + LAN).

To generate certs:  python make_cert.py
"""

import http.server
import socket
import socketserver
import ssl
from pathlib import Path

PORT = 8000
ROOT = Path(__file__).parent
CERT = ROOT / "cert.pem"
KEY = ROOT / "key.pem"


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class DualStackServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # On Windows, Edge resolves `localhost` to ::1 first; an IPv4-only
    # bind drops those with ERR_TIMED_OUT. Binding to "::" with
    # IPV6_V6ONLY=0 accepts both IPv6 and IPv4-mapped connections.
    #
    # ThreadingMixIn so module imports (which trigger many parallel GETs)
    # don't serialize behind the page request.
    address_family = socket.AF_INET6
    allow_reuse_address = True
    daemon_threads = True

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def main() -> None:
    ip = lan_ip()
    use_https = CERT.exists() and KEY.exists()
    scheme = "https" if use_https else "http"

    with DualStackServer(("::", PORT), Handler) as httpd:
        if use_https:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=str(CERT), keyfile=str(KEY))
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        else:
            print("(HTTP mode — phone camera will be blocked. "
                  "Run `python make_cert.py` for HTTPS.)")

        print(f"Laptop:  {scheme}://localhost:{PORT}/")
        print(f"Phone:   {scheme}://{ip}:{PORT}/")
        print("Ctrl-C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
