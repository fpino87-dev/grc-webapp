"""Unit test per la protezione CSV formula injection (core.csv_safe)."""
import io

from core.csv_safe import csv_safe, safe_dict_writer, safe_writer


class TestCsvSafe:
    def test_formula_triggers_are_prefixed(self):
        # Valori che iniziano con un trigger ma NON sono numeri puri → prefissati.
        for payload in ("=1+1", "-2+3", "@SUM(A1)", "=cmd|' /c calc'!A1", "+SUM(A1)", "-cmd"):
            out = csv_safe(payload)
            assert out.startswith("'"), payload
            assert out[1:] == payload

    def test_tab_and_cr_are_prefixed(self):
        assert csv_safe("\tfoo").startswith("'")
        assert csv_safe("\rfoo").startswith("'")

    def test_plain_numbers_are_not_mangled(self):
        for n in ("5", "-5", "+3.2", "-0.1", "1e3", "-2.5e-4"):
            assert csv_safe(n) == n, n

    def test_safe_text_untouched(self):
        for s in ("ciao", "A.5.1", "2026-01-01", "Policy approvata"):
            assert csv_safe(s) == s

    def test_none_and_non_str(self):
        assert csv_safe(None) == ""
        assert csv_safe(42) == "42"
        assert csv_safe(True) == "True"


class TestSafeWriter:
    def test_writer_sanitizes_each_cell(self):
        buf = io.StringIO()
        w = safe_writer(buf)
        w.writerow(["=danger", "ok", "-3"])
        line = buf.getvalue().strip()
        # la cella formula è quotata e prefissata, il numero resta intatto
        assert "'=danger" in line
        assert "ok" in line
        assert "-3" in line and "'-3" not in line

    def test_dict_writer_sanitizes_values(self):
        buf = io.StringIO()
        w = safe_dict_writer(buf, fieldnames=["a", "b"])
        w.writeheader()
        w.writerow({"a": "=evil", "b": "plain"})
        out = buf.getvalue()
        assert "'=evil" in out
        assert "plain" in out
