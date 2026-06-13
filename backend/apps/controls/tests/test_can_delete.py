"""Unit test per la regola unica di eliminabilità `can_delete_instance` (2.2).

La regola è una sola sorgente di verità condivisa tra il guard di
`delete_control_instance` e il flag `can_delete` esposto da detail-info: il
frontend non la ricalcola più, così UI e backend non possono divergere.
"""
from types import SimpleNamespace

from apps.controls.services import can_delete_instance


def _inst(status):
    return SimpleNamespace(status=status)


def _user(is_superuser):
    return SimpleNamespace(is_superuser=is_superuser)


def test_non_valutato_is_deletable_by_anyone():
    assert can_delete_instance(_inst("non_valutato"), _user(False)) is True


def test_evaluated_is_not_deletable_by_normal_user():
    for status in ("compliant", "gap", "parziale", "na"):
        assert can_delete_instance(_inst(status), _user(False)) is False, status


def test_evaluated_is_deletable_by_superuser():
    assert can_delete_instance(_inst("compliant"), _user(True)) is True


def test_missing_is_superuser_attr_defaults_false():
    assert can_delete_instance(_inst("compliant"), SimpleNamespace()) is False
