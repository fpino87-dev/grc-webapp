"""
Test import framework JSON: preview, upsert DB e — regressione — il file
viene scritto in BASE_DIR/frameworks (prima del fix finiva in /frameworks,
fuori dal mount, per un parents[N] sbagliato dopo il vecchio layout).
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="fwimport@test.com", email="fwimport@test.com", password="x"
    )


@pytest.fixture
def payload():
    return {
        "code": "FWTEST",
        "name": "Framework Test",
        "version": "1.0",
        "published_at": "2026-01-01",
        "domains": [
            {"code": "D1", "translations": {"it": {"name": "Dominio 1"}, "en": {"name": "Domain 1"}}},
        ],
        "controls": [
            {
                "external_id": "FT-1.1",
                "domain": "D1",
                "translations": {"it": {"title": "Controllo 1"}, "en": {"title": "Control 1"}},
            },
        ],
    }


def test_preview_returns_sha_counts_languages(db, payload):
    from apps.controls.services import preview_framework_import

    preview = preview_framework_import(payload)
    assert len(preview["sha256"]) == 64
    assert preview["framework"]["code"] == "FWTEST"
    assert preview["counts"] == {"domains": 1, "controls": 1, "mappings": 0}
    assert preview["languages"] == ["en", "it"]


def test_preview_rejects_invalid_payload(db):
    from apps.controls.services import preview_framework_import

    with pytest.raises(ValidationError):
        preview_framework_import({"code": "X", "controls": []})


@pytest.mark.django_db
def test_import_upserts_db_without_file(payload, superuser):
    from apps.controls.models import Control, ControlDomain, Framework
    from apps.controls.services import import_framework_payload

    result = import_framework_payload(payload, superuser, overwrite_json_file=False)

    assert result["ok"] is True
    fw = Framework.objects.get(code="FWTEST")
    assert fw.version == "1.0"
    assert ControlDomain.objects.filter(framework=fw, code="D1").exists()
    assert Control.objects.filter(framework=fw, external_id="FT-1.1").exists()


@pytest.mark.django_db
def test_import_writes_json_under_base_dir_frameworks(payload, superuser, settings, tmp_path):
    """Regressione: il JSON deve finire in BASE_DIR/frameworks/<code>.json."""
    from apps.controls.services import import_framework_payload

    settings.BASE_DIR = tmp_path
    import_framework_payload(payload, superuser, overwrite_json_file=True)

    expected = tmp_path / "frameworks" / "FWTEST.json"
    assert expected.is_file()
    assert '"code": "FWTEST"' in expected.read_text(encoding="utf-8")
