import pytest
from django.db import connection

from apps.auth_grc.management.commands.reset_test_db import TABLES_TO_TRUNCATE


@pytest.mark.django_db
def test_reset_tables_exist():
    """Guardia: ogni tabella da svuotare esiste (rimuovere un modello senza
    aggiornare l'elenco rompeva il reset, la transazione si interrompeva)."""
    existing = set(connection.introspection.table_names())
    assert [t for t in TABLES_TO_TRUNCATE if t not in existing] == []
