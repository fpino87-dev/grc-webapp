"""Atomic accounting of cloud requests. No provider calls inside DB locks."""

from calendar import monthrange
from datetime import date

from django.db import transaction
from django.utils import timezone


def budget_period(today, reset_day):
    day = min(max(reset_day, 1), 31)
    current = today.replace(day=min(day, monthrange(today.year, today.month)[1]))
    if today >= current:
        return current
    year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    return date(year, month, min(day, monthrange(year, month)[1]))


def _reset_locked(config):
    period = budget_period(timezone.localdate(), config.budget_reset_day)
    if config.last_budget_reset is None or config.last_budget_reset < period:
        config.tokens_used_month = 0
        config.last_budget_reset = period
        config.fallback_notified = False
        type(config).objects.filter(pk=config.pk).update(
            tokens_used_month=0,
            last_budget_reset=period,
            fallback_notified=False,
        )
    return config.last_budget_reset


@transaction.atomic
def reset_budget(config):
    locked = type(config).objects.select_for_update().get(pk=config.pk)
    _reset_locked(locked)
    for field in ("tokens_used_month", "last_budget_reset", "fallback_notified"):
        setattr(config, field, getattr(locked, field))


@transaction.atomic
def reserve_budget(config, amount):
    locked = type(config).objects.select_for_update().get(pk=config.pk)
    period = _reset_locked(locked)
    if amount <= 0 or locked.tokens_used_month + amount > locked.monthly_token_budget:
        return None
    type(config).objects.filter(pk=config.pk).update(tokens_used_month=locked.tokens_used_month + amount)
    return period


@transaction.atomic
def settle_budget(config, reserved, period, used):
    locked = type(config).objects.select_for_update().get(pk=config.pk)
    # A request completing after a reset must not refund the new month's usage.
    if locked.last_budget_reset == period:
        type(config).objects.filter(pk=config.pk).update(
            tokens_used_month=max(0, locked.tokens_used_month - reserved + max(0, used)),
        )
