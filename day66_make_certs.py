"""
Day 66 : 로컬 HTTPS 서버용 인증서 생성 (로컬 CA → 서버 인증서)
- day66_certs/ca.pem          : 로컬 CA 인증서 (클라이언트 verify에 지정)
- day66_certs/server.pem/.key : 127.0.0.1·localhost용 서버 인증서와 개인키
day66_certs/ 는 .gitignore 등록 (개인키 커밋 금지)
"""

import datetime
import ipaddress
import os
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(BASE_DIR, "day66_certs")
CA_CERT = os.path.join(CERT_DIR, "ca.pem")
SERVER_CERT = os.path.join(CERT_DIR, "server.pem")
SERVER_KEY = os.path.join(CERT_DIR, "server.key")


def _write_key(path, key):
    with open(path, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                  serialization.NoEncryption()))


def _write_cert(path, cert):
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def make_certs(force=False):
    if not force and all(os.path.exists(p) for p in (CA_CERT, SERVER_CERT, SERVER_KEY)):
        print(f"[인증서] 기존 파일 사용: {os.path.relpath(CERT_DIR, BASE_DIR)}/")
        return
    os.makedirs(CERT_DIR, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "QA-Portfolio Local CA")])
    ca_cert = (x509.CertificateBuilder()
               .subject_name(ca_name).issuer_name(ca_name)
               .public_key(ca_key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(now - datetime.timedelta(minutes=5))
               .not_valid_after(now + datetime.timedelta(days=365))
               .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
               .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                                            content_commitment=False, key_encipherment=False,
                                            data_encipherment=False, key_agreement=False,
                                            encipher_only=False, decipher_only=False), critical=True)
               .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
               .sign(ca_key, hashes.SHA256()))

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_cert = (x509.CertificateBuilder()
                   .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")]))
                   .issuer_name(ca_name)
                   .public_key(server_key.public_key())
                   .serial_number(x509.random_serial_number())
                   .not_valid_before(now - datetime.timedelta(minutes=5))
                   .not_valid_after(now + datetime.timedelta(days=90))
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),
                                                               x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                                  critical=False)
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                   .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                                  critical=False)
                   .sign(ca_key, hashes.SHA256()))

    _write_cert(CA_CERT, ca_cert)
    _write_cert(SERVER_CERT, server_cert)
    _write_key(SERVER_KEY, server_key)
    print(f"[인증서] 생성: ca.pem (CN=QA-Portfolio Local CA), server.pem (SAN=localhost, 127.0.0.1)")


if __name__ == "__main__":
    make_certs(force="--force" in sys.argv)
