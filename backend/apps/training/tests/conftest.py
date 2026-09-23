import pytest


@pytest.fixture
def legacy_apps(db):
    """Schema della formazione com'era prima della 0007 (tabelle per persona e
    campi deprecati del corso), ricreato dentro la transazione del test: il
    rollback finale ripristina lo schema attuale. Restituisce i model storici
    di quello stato, come li vedono la 0004, la 0006 e il comando di anteprima."""
    from django.db import connection
    from django.db.migrations.loader import MigrationLoader

    from apps.training.legacy import LEGACY_STATE_NODE

    loader = MigrationLoader(connection)
    state = loader.project_state(LEGACY_STATE_NODE)
    drop = loader.get_migration("training", "0007_drop_legacy_per_person_data")
    with connection.schema_editor() as editor:
        drop.unapply(state.clone(), editor)
    return state.apps
