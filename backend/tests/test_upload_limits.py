"""Test limiti upload e body size (newfix S12)."""
from django.conf import settings


def test_data_upload_max_memory_size_set():
    """JSON body cap ~5 MB per impedire denial-of-memory."""
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE == 5 * 1024 * 1024


def test_file_upload_max_memory_size_set():
    """File >50 MB vengono streamati su disco invece di stare in RAM."""
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == 50 * 1024 * 1024


def test_data_upload_max_number_fields_set():
    """Cap esplicito sul numero di campi POST per richiesta."""
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS == 1000
