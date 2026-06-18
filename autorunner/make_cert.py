"""Generate a self-signed cert + key for the dev server.

Run once:  python make_cert.py
Produces:  cert.pem, key.pem (in this directory)

The cert covers `localhost` and the current LAN IP. The phone will see a
"connection not private" warning the first time — accept it and Chrome
will remember the exception for this origin.

Uses the `cryptography` library (`pip install cryptography`). If it is
not installed, falls back to printing an `openssl` one-liner you can run
by hand.
"""

import socket
import sys
from pathlib import Path

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


def gen_with_cryptography(ip: str) -> None:
    from datetime import datetime, timedelta, timezone
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import ipaddress

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "qr-webrtc dev"),
    ])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address(ip)),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    KEY.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def main() -> int:
    ip = lan_ip()
    try:
        gen_with_cryptography(ip)
    except ImportError:
        print("cryptography not installed. Run one of:")
        print()
        print(f"  pip install cryptography && python {Path(__file__).name}")
        print()
        print("Or use openssl directly:")
        print()
        print(
            f'  openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem '
            f'-out cert.pem -days 365 -subj "/CN=qr-webrtc" '
            f'-addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:{ip}"'
        )
        return 1

    print(f"Wrote {CERT.name} and {KEY.name}.")
    print(f"Covers: localhost, 127.0.0.1, {ip}")
    print("Now run: python serve.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
