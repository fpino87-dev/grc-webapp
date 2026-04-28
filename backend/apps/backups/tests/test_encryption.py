"""Test cifratura at-rest dei backup (newfix R4)."""
from pathlib import Path

import pytest
from django.test import override_settings

from apps.backups import encryption


PASSPHRASE = "test-passphrase-not-prod-key"


def test_is_encryption_enabled_false_when_empty():
    with override_settings(BACKUP_ENCRYPTION_KEY=""):
        assert encryption.is_encryption_enabled() is False


def test_is_encryption_enabled_true_when_set():
    with override_settings(BACKUP_ENCRYPTION_KEY=PASSPHRASE):
        assert encryption.is_encryption_enabled() is True


def test_encrypt_then_decrypt_roundtrip(tmp_path):
    payload = b"sensitive db dump bytes \x00\x01\xff" * 100
    plain = tmp_path / "in.bin"
    plain.write_bytes(payload)
    enc = tmp_path / "out.enc"

    with override_settings(BACKUP_ENCRYPTION_KEY=PASSPHRASE):
        encryption.encrypt_file(plain, enc)
        # encrypt_file rimuove il plaintext sorgente
        assert not plain.exists()
        assert enc.exists()
        # Magic header presente, payload non in chiaro
        data = enc.read_bytes()
        assert data.startswith(b"GRC1")
        assert payload not in data

        decoded = tmp_path / "out.dec"
        encryption.decrypt_file(enc, decoded)
        assert decoded.read_bytes() == payload


def test_decrypt_with_wrong_passphrase_raises(tmp_path):
    plain = tmp_path / "in.bin"
    plain.write_bytes(b"hello world")
    enc = tmp_path / "out.enc"

    with override_settings(BACKUP_ENCRYPTION_KEY=PASSPHRASE):
        encryption.encrypt_file(plain, enc)

    out = tmp_path / "out.dec"
    with override_settings(BACKUP_ENCRYPTION_KEY="wrong-passphrase"):
        with pytest.raises(Exception):
            encryption.decrypt_file(enc, out)


def test_decrypt_rejects_file_without_magic_header(tmp_path):
    bogus = tmp_path / "fake.enc"
    bogus.write_bytes(b"NOT_A_GRC1_FILE_AT_ALL")
    out = tmp_path / "fake.dec"
    with override_settings(BACKUP_ENCRYPTION_KEY=PASSPHRASE):
        with pytest.raises(ValueError, match="magic"):
            encryption.decrypt_file(bogus, out)


def test_encrypt_without_passphrase_raises(tmp_path):
    plain = tmp_path / "in.bin"
    plain.write_bytes(b"hello")
    enc = tmp_path / "out.enc"
    with override_settings(BACKUP_ENCRYPTION_KEY=""):
        with pytest.raises(RuntimeError, match="non configurata"):
            encryption.encrypt_file(plain, enc)
