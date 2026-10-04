"""
Cifratura at-rest dei backup pg_dump (newfix R4).

Usa AES-256-GCM via la libreria `cryptography` (gia' dipendenza per Fernet),
con chiave derivata dalla passphrase `settings.BACKUP_ENCRYPTION_KEY` tramite
PBKDF2-HMAC-SHA256 (200_000 iterazioni). Lo stretching della passphrase
permette di usare valori arbitrari senza degradare la robustezza.

Formato file cifrato (streaming, compatibile con gli archivi GRC1 esistenti):

    [magic 4B = b"GRC1"]
    [salt   16B]
    [nonce  12B]
    [ciphertext + GCM tag (16B finali)]

La separazione tra `BACKUP_ENCRYPTION_KEY` (passphrase backup) e `FERNET_KEY`
(credenziali SMTP / API key OSINT) e' deliberata: chi compromette le
credenziali del backup deve restare separato da chi compromette il database
chiave operativo.
"""
from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import tempfile
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings


_MAGIC = b"GRC1"
_SALT_LEN = 16
_NONCE_LEN = 12
_KDF_ITERATIONS = 200_000


def is_encryption_enabled() -> bool:
    return bool(getattr(settings, "BACKUP_ENCRYPTION_KEY", "") or "")


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def _write_private(destination, writer):
    """Publish only complete authenticated output; temporary files are mode 0600."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            writer(output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def encrypt_file(plain_path: Path, enc_path: Path) -> None:
    passphrase = settings.BACKUP_ENCRYPTION_KEY
    if not passphrase:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY non configurata.")
    salt, nonce = os.urandom(_SALT_LEN), os.urandom(_NONCE_LEN)
    encryptor = Cipher(algorithms.AES(_derive_key(passphrase, salt)), modes.GCM(nonce)).encryptor()

    def write(output):
        output.write(_MAGIC + salt + nonce)
        with open(plain_path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                output.write(encryptor.update(chunk))
        output.write(encryptor.finalize())
        output.write(encryptor.tag)

    _write_private(enc_path, write)
    plain_path.unlink()


def decrypt_file(enc_path: Path, plain_path: Path) -> None:
    passphrase = settings.BACKUP_ENCRYPTION_KEY
    if not passphrase:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY non configurata.")
    header_size = len(_MAGIC) + _SALT_LEN + _NONCE_LEN
    with open(enc_path, "rb") as source:
        header = source.read(header_size)
        if len(header) != header_size or not header.startswith(_MAGIC):
            raise ValueError("File non cifrato o magic header errato.")
        size = source.seek(0, os.SEEK_END)
        remaining = size - header_size - 16
        if remaining < 0:
            raise ValueError("Truncated encrypted backup.")
        source.seek(-16, os.SEEK_END)
        tag = source.read(16)
        source.seek(header_size)
        salt = header[4:4 + _SALT_LEN]
        nonce = header[4 + _SALT_LEN:]
        decryptor = Cipher(algorithms.AES(_derive_key(passphrase, salt)), modes.GCM(nonce, tag)).decryptor()

        def write(output):
            left = remaining
            while left:
                chunk = source.read(min(left, 1024 * 1024))
                if not chunk:
                    raise ValueError("Truncated encrypted backup.")
                left -= len(chunk)
                output.write(decryptor.update(chunk))
            output.write(decryptor.finalize())

        _write_private(plain_path, write)
