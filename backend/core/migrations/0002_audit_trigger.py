from django.db import migrations

SQL = """
CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS TRIGGER AS $$
BEGIN RAISE EXCEPTION 'AuditLog is append-only. id=%', OLD.id; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER audit_no_mutation BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
CREATE INDEX IF NOT EXISTS idx_auditlog_entity ON audit_log(entity_type, entity_id, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_auditlog_user   ON audit_log(user_id, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_auditlog_action ON audit_log(action_code, timestamp_utc DESC);
"""
REVERSE = """
DROP TRIGGER IF EXISTS audit_no_mutation ON audit_log;
DROP FUNCTION IF EXISTS prevent_audit_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunSQL(SQL, reverse_sql=REVERSE)]

