"""Pilot review regressions. Synthetic data; no external provider calls."""

import io
import tarfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from rest_framework.test import APIClient

from apps.ai_engine.models import AiProviderConfig
from apps.ai_engine.services import budget_period, reserve_budget, settle_budget
from apps.auth_grc.models import UserPlantAccess
from apps.backups import archive, encryption
from apps.plants.models import Plant
from core.uploads import validate_uploaded_file


@pytest.fixture
def scope_data(db):
    user = get_user_model().objects.create_user(username="review-user", password="example-only")
    a = Plant.objects.create(code="REVIEW-A", name="Review A", country="IT")
    b = Plant.objects.create(code="REVIEW-B", name="Review B", country="IT")
    grant = UserPlantAccess.objects.create(user=user, role="plant_manager", scope_type="single_plant")
    grant.scope_plants.add(a)
    client = APIClient()
    client.force_authenticate(user)
    return user, a, b, client


def test_asset_eol_respects_plant_scope(scope_data):
    from apps.assets.models import AssetIT

    user, a, b, client = scope_data
    visible = AssetIT.objects.create(plant=a, name="allowed", eol_date=date(2000, 1, 1))
    hidden = AssetIT.objects.create(plant=b, name="hidden", eol_date=date(2000, 1, 1))
    response = client.get("/api/v1/assets/it/eol/")
    assert response.status_code == 200
    ids = {str(row["id"]) for row in response.data}
    assert str(visible.pk) in ids
    assert str(hidden.pk) not in ids


def test_foreign_asset_dependency_rejected(scope_data):
    from apps.assets.models import AssetIT

    user, a, b, client = scope_data
    local = AssetIT.objects.create(plant=a, name="local")
    foreign = AssetIT.objects.create(plant=b, name="foreign")
    response = client.post(
        "/api/v1/assets/dependencies/",
        {
            "from_asset": str(local.pk),
            "to_asset": str(foreign.pk),
            "dep_type": "connesso_a",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "to_asset" in response.data


def test_asset_process_fk_outside_scope_rejected(scope_data):
    from apps.assets.models import AssetIT
    from apps.bia.models import CriticalProcess

    user, a, b, client = scope_data
    asset = AssetIT.objects.create(plant=a, name="local")
    foreign = CriticalProcess.objects.create(plant=b, name="private process")
    response = client.patch(f"/api/v1/assets/it/{asset.pk}/", {"processes": [str(foreign.pk)]}, format="json")
    assert response.status_code == 400
    assert not asset.processes.exists()


def test_asset_maintainer_supplier_follows_supplier_visibility(scope_data):
    from apps.assets.models import AssetIT
    from apps.suppliers.models import Supplier

    user, a, b, client = scope_data
    asset = AssetIT.objects.create(plant=a, name="local")
    shared = Supplier.objects.create(name="Shared supplier")
    shared.plants.add(a, b)
    foreign = Supplier.objects.create(name="Foreign supplier")
    foreign.plants.add(b)
    org_wide = Supplier.objects.create(name="Org supplier")

    for supplier in (shared, org_wide):
        response = client.patch(
            f"/api/v1/assets/it/{asset.pk}/", {"maintainer_supplier": str(supplier.pk)}, format="json",
        )
        assert response.status_code == 200, response.data
    response = client.patch(
        f"/api/v1/assets/it/{asset.pk}/", {"maintainer_supplier": str(foreign.pk)}, format="json",
    )
    assert response.status_code == 400


def test_role_cannot_borrow_scope_from_read_only_assignment(scope_data):
    user, a, b, client = scope_data
    grant = UserPlantAccess.objects.create(user=user, role="external_auditor", scope_type="org")
    response = client.post("/api/v1/assets/it/", {"plant": str(b.pk), "name": "not authorized"}, format="json")
    assert response.status_code == 403
    grant.refresh_from_db()


@pytest.mark.django_db
def test_disabled_user_cannot_complete_mfa():
    user = get_user_model().objects.create_user(username="disabled-mfa", is_active=False)
    token = signing.dumps({"uid": str(user.pk)}, salt="grc-mfa-token")
    with patch("core.jwt.devices_for_user") as devices:
        response = APIClient().post("/api/token/mfa/", {"mfa_token": token, "otp_code": "123456"})
    assert response.status_code == 401
    devices.assert_not_called()


def test_cookie_refresh_rejects_untrusted_same_site_origin():
    response = APIClient().post("/api/token/refresh/", {}, HTTP_ORIGIN="https://untrusted.example")
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("today", "day", "expected"),
    [
        (date(2026, 3, 7), 1, date(2026, 3, 1)),
        (date(2026, 1, 2), 15, date(2025, 12, 15)),
        (date(2026, 2, 28), 31, date(2026, 2, 28)),
        (date(2028, 2, 29), 31, date(2028, 2, 29)),
    ],
)
def test_budget_period_edges(today, day, expected):
    assert budget_period(today, day) == expected


@pytest.mark.django_db
def test_budget_resets_after_missed_day_and_stale_settlement_does_not_refund():
    config = AiProviderConfig.objects.create(
        tokens_used_month=90, monthly_token_budget=100, last_budget_reset=date(2026, 1, 1)
    )
    with patch("apps.ai_engine.services.timezone.localdate", return_value=date(2026, 3, 7)):
        period = reserve_budget(config, 80)
        assert period == date(2026, 3, 1)
        assert reserve_budget(config, 30) is None
        settle_budget(config, 80, period, 20)
        config.refresh_from_db()
        assert config.tokens_used_month == 20
    with patch("apps.ai_engine.services.timezone.localdate", return_value=date(2026, 4, 9)):
        reserve_budget(config, 50)
        settle_budget(config, 80, period, 1)
        config.refresh_from_db()
        assert config.tokens_used_month == 50


@pytest.mark.django_db(transaction=True)
def test_concurrent_budget_reservations_cannot_overspend():
    config = AiProviderConfig.objects.create(monthly_token_budget=100)
    barrier = Barrier(4)

    def reserve(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return reserve_budget(config, 60)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(reserve, range(4)))
    assert sum(result is not None for result in results) == 1
    config.refresh_from_db()
    assert config.tokens_used_month == 60


@pytest.mark.django_db
def test_local_only_never_calls_cloud(settings):
    from apps.ai_engine.router import route

    settings.AI_CLOUD_ENABLED = False
    AiProviderConfig.objects.create(task_routing={"review": "cloud"})
    with (
        patch("apps.ai_engine.router._call_cloud") as cloud,
        patch("apps.ai_engine.router.resolve_cloud_model") as catalog,
        patch("apps.ai_engine.router._call_ollama", return_value="local"),
    ):
        result = route("review", "synthetic")
    assert result["provider"] == "ollama"
    cloud.assert_not_called()
    catalog.assert_not_called()


@pytest.mark.django_db
def test_system_prompt_sanitized_even_with_opt_out(settings):
    from apps.ai_engine.router import route

    settings.AI_CLOUD_ENABLED = True
    AiProviderConfig.objects.create(task_routing={"review": "cloud"})
    with (
        patch("apps.ai_engine.router._call_cloud", return_value=("ok", 2)) as cloud,
        patch("apps.ai_engine.router.resolve_cloud_model", return_value=("mock", None)),
    ):
        route("review", "test@example.org", system="admin@example.org", sanitize=False)
    args = cloud.call_args.args
    assert "test@example.org" not in args[1]
    assert "admin@example.org" not in args[2]


@pytest.mark.django_db
def test_sanitizer_ipv6_and_iban():
    from apps.ai_engine.sanitizer import Sanitizer

    text = "2001:db8::1234 IBAN IT60X0542811101000000123456 ISO 27001:2022"
    result, _ = Sanitizer().sanitize({"text": text})
    assert "2001:db8" not in result["text"]
    assert "IT60X" not in result["text"]
    assert "ISO 27001:2022" in result["text"]


@pytest.mark.parametrize(
    "name,kind,link",
    [
        ("media/../../escape", tarfile.REGTYPE, ""),
        ("media/link", tarfile.SYMTYPE, "/tmp"),
        ("media/link", tarfile.LNKTYPE, "../../escape"),
        ("media/device", tarfile.CHRTYPE, ""),
    ],
)
def test_backup_rejects_unsafe_members_before_extraction(tmp_path, settings, name, kind, link):
    target = tmp_path / "unsafe.tar"
    with tarfile.open(target, "w") as tar:
        member = tarfile.TarInfo(name)
        member.type, member.linkname = kind, link
        tar.addfile(member)
    settings.MEDIA_ROOT = tmp_path / "live"
    with pytest.raises(ValueError):
        archive.restore_media(target)
    assert not (tmp_path / "live").exists()


def test_encryption_legacy_compatibility_and_tamper_no_plaintext(tmp_path, settings):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    settings.BACKUP_ENCRYPTION_KEY = "synthetic-review-key"
    salt, nonce = b"s" * 16, b"n" * 12
    payload = b"synthetic" * 10000
    enc, plain = tmp_path / "old.enc", tmp_path / "plain"
    legacy = (
        b"GRC1"
        + salt
        + nonce
        + AESGCM(encryption._derive_key(settings.BACKUP_ENCRYPTION_KEY, salt)).encrypt(nonce, payload, None)
    )
    enc.write_bytes(legacy)
    encryption.decrypt_file(enc, plain)
    assert plain.read_bytes() == payload
    enc.write_bytes(legacy[:-1] + bytes([legacy[-1] ^ 1]))
    untouched = tmp_path / "untouched"
    with pytest.raises(Exception):
        encryption.decrypt_file(enc, untouched)
    assert not untouched.exists()
    assert plain.stat().st_mode & 0o777 == 0o600


def test_ooxml_bomb_rejected_even_when_mime_is_office():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive_file:
        archive_file.writestr("[Content_Types].xml", "<Types/>")
        archive_file.writestr("word/document.xml", "x" * 1000000)
    upload = SimpleUploadedFile("bomb.docx", data.getvalue())
    with patch(
        "core.uploads.magic.from_buffer",
        return_value="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        with pytest.raises(ValidationError):
            validate_uploaded_file(upload)


@pytest.mark.django_db(transaction=True)
def test_concurrent_audit_chain_has_one_head():
    from core.audit import AuditLog, log_action, verify_audit_integrity

    entity = Plant.objects.create(code="AUDIT-RACE", name="Synthetic")
    barrier = Barrier(4)

    def append(i):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            log_action(user=None, action_code="review.concurrent", level="L2", entity=entity, payload={"i": i})
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(append, range(4)))
    rows = AuditLog.objects.filter(action_code="review.concurrent")
    assert rows.count() == 4
    assert rows.filter(prev_hash="0" * 64).count() == 1
    result = verify_audit_integrity(rows)
    assert result["ok"] and result["branched"] == {}


@pytest.mark.django_db
def test_historical_branch_is_warning_not_corruption():
    import uuid

    from django.utils import timezone

    from core.audit import GENESIS_HASH, AuditLog, _compute_hash_v2, verify_audit_integrity

    def add(prev, i):
        ts = timezone.now()
        fields = dict(user_id=uuid.UUID(int=0), action_code="review.branch", level="L2",
                      entity_type="branchtest", entity_id=uuid.uuid4(), payload={"i": i})
        digest = _compute_hash_v2(timestamp_utc=ts, prev_hash=prev, **fields)
        return AuditLog.objects.create(timestamp_utc=ts, prev_hash=prev, record_hash=digest,
                                       hash_version="v2", **fields)

    head = add(GENESIS_HASH, 0)
    add(head.record_hash, 1)
    add(head.record_hash, 2)
    result = verify_audit_integrity(AuditLog.objects.filter(entity_type="branchtest"))
    assert result["ok"]
    assert result["branched"] == {"branchtest": 1}


@pytest.mark.django_db(transaction=True)
def test_refresh_rotation_has_only_one_concurrent_winner():
    from core.jwt import _issue_jwt

    user = get_user_model().objects.create_user(username="refresh-race")
    refresh = _issue_jwt(user)["refresh"]
    barrier = Barrier(2)

    def rotate(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return APIClient().post("/api/token/refresh/", {"refresh": refresh}).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(rotate, range(2))) == [200, 401]


def test_production_checks_reject_missing_backup_key(settings):
    from core.checks import production_secrets

    settings.BACKUP_ENCRYPTION_KEY = ""
    assert "grc.E003" in {error.id for error in production_secrets(None)}


@pytest.mark.django_db
def test_nonzero_restore_status_never_treated_as_success(tmp_path, settings):
    from apps.backups.models import BackupRecord
    from apps.backups import services

    user = get_user_model().objects.create_user(username="restore-review")
    (tmp_path / "review.dump").write_bytes(b"PGDMPsynthetic")
    record = BackupRecord.objects.create(filename="review.dump", status="completed")
    with patch.object(services, "BACKUP_DIR", tmp_path), patch.object(services.subprocess, "run") as run:
        run.return_value.returncode = 1
        run.return_value.stderr = "errore localizzato senza parola inglese"
        with pytest.raises(RuntimeError):
            services.restore_backup(record.pk, user)
    assert "--single-transaction" in run.call_args.args[0]
    assert "--exit-on-error" in run.call_args.args[0]
    record.refresh_from_db()
    assert record.status != "restored"


def test_site_auditor_cannot_read_global_audit_trail(scope_data):
    user, a, b, client = scope_data
    grant = UserPlantAccess.objects.create(user=user, role="external_auditor", scope_type="single_plant")
    grant.scope_plants.add(a)
    assert client.get("/api/v1/audit-trail/audit-logs/").status_code == 403
    from apps.audit_trail.permissions import AuditLogReadPermission
    from types import SimpleNamespace

    assert not AuditLogReadPermission().has_permission(SimpleNamespace(user=user), None)


def test_staff_kpi_ingest_cannot_cross_scope(scope_data):
    user, a, b, client = scope_data
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    response = client.post(
        "/api/v1/kpi-ingest/",
        {
            "kpi_code": "backup_success_rate",
            "plant": str(b.pk),
            "value": 90,
            "source": "review",
        },
        format="json",
    )
    assert response.status_code == 403


def test_document_link_cannot_mutate_foreign_control(scope_data):
    from apps.documents.models import Document
    from apps.controls.models import Framework, Control, ControlInstance
    from apps.documents.services import link_document_controls
    from rest_framework.exceptions import PermissionDenied

    user, a, b, client = scope_data
    framework = Framework.objects.create(code="REVIEW", name="Synthetic", version="1", published_at=date(2026, 1, 1))
    control = Control.objects.create(framework=framework, external_id="review", translations={})
    foreign = ControlInstance.objects.create(control=control, plant=b)
    document = Document.objects.create(title="Synthetic", category="politica", plant=a)
    with pytest.raises(PermissionDenied):
        link_document_controls(document, user, [str(foreign.pk)])
    assert not foreign.documents.exists()


def test_encrypted_field_uses_explicit_key_and_reads_legacy(settings):
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from apps.notifications.models import EncryptedCharField

    key = Fernet.generate_key()
    settings.FERNET_KEYS = [key.decode()]
    field = EncryptedCharField()
    encrypted = field.get_prep_value("synthetic-secret")
    assert Fernet(key).decrypt(encrypted.encode()) == b"synthetic-secret"
    legacy = Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()))
    old = legacy.encrypt(b"old-secret").decode()
    assert field.from_db_value(old, None, None) == "old-secret"
    assert Fernet(key).decrypt(field.get_prep_value(old).encode()) == b"old-secret"
    with pytest.raises(ValueError):
        field.from_db_value(Fernet(Fernet.generate_key()).encrypt(b"unknown").decode(), None, None)


@pytest.mark.django_db
def test_password_change_revokes_access_and_refresh():
    from core.jwt import _issue_jwt
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import AuthenticationFailed

    user = get_user_model().objects.create_user(username="password-revoke", password="old-example")
    pair = _issue_jwt(user)
    auth = JWTAuthentication()
    assert auth.get_user(auth.get_validated_token(pair["access"])).pk == user.pk
    user.set_password("new-example")
    user.save(update_fields=["password"])
    with pytest.raises(AuthenticationFailed):
        auth.get_user(auth.get_validated_token(pair["access"]))
    assert APIClient().post("/api/token/refresh/", {"refresh": pair["refresh"]}).status_code == 401
    current = _issue_jwt(user)
    assert APIClient().post("/api/token/refresh/", {"refresh": current["refresh"]}).status_code == 200


@pytest.mark.django_db
def test_failed_scheduled_backup_retries_without_retention():
    from apps.backups.tasks import auto_backup_task
    from types import SimpleNamespace

    get_user_model().objects.create_superuser(username="backup-retry", password="example-only")
    with (
        patch("apps.backups.services.create_backup", return_value=SimpleNamespace(status="failed")),
        patch("apps.backups.services.cleanup_old_backups") as cleanup,
    ):
        with pytest.raises(RuntimeError, match="existing backups retained"):
            auto_backup_task.run()
    cleanup.assert_not_called()


def test_media_rollback_failure_preserves_original_copy(tmp_path, settings):
    import os

    media = tmp_path / "media"
    media.mkdir()
    (media / "original.txt").write_text("original")
    settings.MEDIA_ROOT = str(media)
    backup = tmp_path / "backup.tar"
    with tarfile.open(backup, "w") as tar:
        member = tarfile.TarInfo("media/new.txt")
        member.size = 3
        tar.addfile(member, io.BytesIO(b"new"))
    rename = os.rename

    def fail_install_and_rollback(source, target):
        if str(source) == str(media):
            return rename(source, target)
        raise OSError("simulated filesystem failure")

    with patch("apps.backups.archive.os.rename", side_effect=fail_install_and_rollback):
        with pytest.raises(OSError):
            archive.restore_media(backup)
    preserved = list(tmp_path.glob(".media_old_*/original.txt"))
    assert len(preserved) == 1
    assert preserved[0].read_text() == "original"


@pytest.mark.parametrize("action", ["confirm", "ignore"])
def test_ai_acknowledgement_requires_interaction_owner(scope_data, action):
    from apps.ai_engine.models import AiInteractionLog

    user, a, b, client = scope_data
    other = get_user_model().objects.create_user(username="other-ai-user")
    log = AiInteractionLog.objects.create(
        user_id=other.pk,
        entity_id=b.pk,
        function="review",
        module_source="M20",
        model_used="mock",
        input_hash="0" * 64,
        output_ai="synthetic",
    )
    body = {"interaction_id": str(log.pk), "action": action, "final_text": "replacement"}
    assert client.post("/api/v1/ai/confirm/", body, format="json").status_code == 404
    log.refresh_from_db()
    assert not log.ignored and log.confirmed_at is None
    log.user_id = user.pk
    log.save(update_fields=["user_id"])
    assert client.post("/api/v1/ai/confirm/", body, format="json").status_code == 200
    log.refresh_from_db()
    assert log.ignored if action == "ignore" else log.confirmed_at is not None


def test_backup_plaintext_files_are_private(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "no-media")
    source, backup, extracted = (tmp_path / name for name in ("source", "backup.tar", "dump"))
    source.write_bytes(b"PGDMPsynthetic")
    archive.build_archive(source, backup)
    archive.extract_db_dump(backup, extracted)
    assert backup.stat().st_mode & 0o777 == 0o600
    assert extracted.stat().st_mode & 0o777 == 0o600


@pytest.mark.django_db
def test_failed_backup_encryption_removes_plaintext(tmp_path, settings):
    from apps.backups import services
    from types import SimpleNamespace

    settings.MEDIA_ROOT = str(tmp_path / "no-media")
    settings.BACKUP_ENCRYPTION_KEY = "synthetic-review-key"
    user = get_user_model().objects.create_user(username="backup-encryption-failure")

    def dump(cmd, **kwargs):
        from pathlib import Path

        target = Path(cmd[-1])
        assert target.stat().st_mode & 0o777 == 0o600
        target.write_bytes(b"PGDMPsynthetic")
        return SimpleNamespace(returncode=0)

    with (
        patch.object(services, "BACKUP_DIR", tmp_path),
        patch.object(services.subprocess, "run", side_effect=dump),
        patch.object(encryption, "encrypt_file", side_effect=OSError("synthetic failure")),
    ):
        record = services.create_backup(user)
    assert record.status == "failed"
    assert not list(tmp_path.glob("backup_*"))
