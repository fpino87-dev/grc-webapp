"""
Cifratura at-rest dei backup pg_dump (newfix R4).

Usa AES-256-GCM via la libreria `cryptography` (gia' dipendenza per Fernet),
con chiave derivata dalla passphrase `settings.BACKUP_ENCRYPTION_KEY` tramite
PBKDF2-HMAC-SHA256 (200_000 iterazioni). Lo stretching della passphrase
permette di usare valori arbitrari senza degradare la robustezza.

Formato file cifrato (single shot, niente streaming — i dump pg_dump in
ambiente single-tenant sono dell'ordine dei MB/centinaia di MB, non GB):

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
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
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


def encrypt_file(plain_path: Path, enc_path: Path) -> None:
    """Cifra in-place: legge plain_path, scrive enc_path, elimina plain_path."""
    passphrase = settings.BACKUP_ENCRYPTION_KEY
    if not passphrase:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY non configurata.")
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    with open(plain_path, "rb") as f:
        plaintext = f.read()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    with open(enc_path, "wb") as f:
        f.write(_MAGIC)
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)
    plain_path.unlink()


def decrypt_file(enc_path: Path, plain_path: Path) -> None:
    """Decifra: legge enc_path, scrive plain_path. Lascia entrambi i file."""
    passphrase = settings.BACKUP_ENCRYPTION_KEY
    if not passphrase:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY non configurata.")
    with open(enc_path, "rb") as f:
        data = f.read()
    if not data.startswith(_MAGIC):
        raise ValueError("File non cifrato o magic header errato.")
    body = data[len(_MAGIC):]
    salt = body[:_SALT_LEN]
    nonce = body[_SALT_LEN:_SALT_LEN + _NONCE_LEN]
    ciphertext = body[_SALT_LEN + _NONCE_LEN:]
    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    with open(plain_path, "wb") as f:
        f.write(plaintext)
