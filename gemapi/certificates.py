import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509.oid import NameOID
from loguru import logger

# TODO:
# logic to inspect/re-generate cert when needed

_DEFAULT_DIRECTORY = Path(".")


class CertificateManager:
    def __init__(
        self,
        hostnames: list[str],
        directory: Path | None = None,
        certfile: str = "cert.pem",
        keyfile: str = "key.pem",
    ) -> None:
        self._hostnames = hostnames
        self._directory = directory or _DEFAULT_DIRECTORY
        self._certfile = certfile
        self._keyfile = keyfile

    def initialize(self) -> None:
        logger.info("Initializing certificate manager")
        self._setup_directory()

        if self.keyfile.exists() and self.certfile.exists():
            cert = self.certificate
            if self._is_certificate_matching_configuration(cert):
                logger.info("Found existing certificate")
                if datetime.datetime.now(
                    datetime.timezone.utc
                ) > self._certificate_expires_at(cert):
                    logger.info("Certificate has expired")
                else:
                    return None
            else:
                logger.info("Existing certificate does not match current configuration")

        self._generate_certificate()

    def certificate_expires_at(self) -> datetime.datetime:
        return self._certificate_expires_at(self.certificate)

    def _setup_directory(self) -> None:
        if not self._directory.exists():
            self._directory.mkdir(parents=True)

    @property
    def keyfile(self) -> Path:
        return self._directory / self._keyfile

    @property
    def certfile(self) -> Path:
        return self._directory / self._certfile

    @property
    def certificate(self) -> x509.Certificate:
        return x509.load_pem_x509_certificate(self.certfile.read_bytes())

    def _is_certificate_matching_configuration(self, cert: x509.Certificate) -> bool:
        subject_hostname = cert.subject.rfc4514_string().removeprefix("CN=")
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        hostnames = {subject_hostname} | {dns_name.value for dns_name in san_ext.value}
        return hostnames == set(self._hostnames)

    def _certificate_expires_at(self, cert: x509.Certificate) -> datetime.datetime:
        return cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)

    def _generate_private_key(self) -> ed25519.Ed25519PrivateKey:
        if not self.keyfile.exists():
            logger.info("Generating private key")
            private_key = ed25519.Ed25519PrivateKey.generate()
            private_bytes = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            self.keyfile.write_bytes(private_bytes)
            return private_key
        else:
            return load_pem_private_key(self.keyfile.read_bytes(), None)  # type: ignore

    def _generate_certificate(self) -> None:
        private_key = self._generate_private_key()

        logger.info("Generating certificate")

        one_day = datetime.timedelta(days=1)
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, self._hostnames[0])])
        )
        builder = builder.issuer_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, self._hostnames[0])])
        )
        builder = builder.not_valid_before(datetime.datetime.today() - one_day)
        builder = builder.not_valid_after(datetime.datetime.today() + (one_day * 365))
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.public_key(private_key.public_key())
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(hostname) for hostname in self._hostnames]
            ),
            critical=False,
        )
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        )

        request = builder.sign(private_key, None, default_backend())
        cert_bytes = request.public_bytes(serialization.Encoding.PEM)
        self.certfile.write_bytes(cert_bytes)
