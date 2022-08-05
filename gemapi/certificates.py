import datetime

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.x509.oid import NameOID

# TODO:
# logic to inspect/re-generate cert when needed


def build_certificate(hostname: str) -> None:
    one_day = datetime.timedelta(days=1)
    private_key = ed25519.Ed25519PrivateKey.generate()
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    )
    builder = builder.issuer_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    )
    builder = builder.not_valid_before(datetime.datetime.today() - one_day)
    builder = builder.not_valid_after(datetime.datetime.today() + (one_day * 365))
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(private_key.public_key())
    builder = builder.add_extension(
        x509.SubjectAlternativeName(
            [
                x509.DNSName(hostname),
            ]
        ),
        critical=False,
    )
    builder = builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True
    )

    request = builder.sign(private_key, None, default_backend())
    pub = request.public_bytes(serialization.Encoding.PEM)
    priv = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    with open("key.pem", "wb") as f:
        f.write(priv)

    with open("cert.pem", "wb") as f:
        f.write(pub)
