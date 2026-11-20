from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.translation import get_language


def sale_ends_at():
    """Joriy aksiya oy oxirida tugaydi (sanoq vaqti saytda ko‘rsatiladi)."""
    now = timezone.localtime()
    first_next = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
    return timezone.make_aware(datetime.combine(first_next.date(), time.min)) - timedelta(seconds=1)


CURRENCY = {"uz": "so‘m", "ru": "сум", "en": "UZS"}


def som(value):
    """1250000 → «1 250 000 so‘m» / «1 250 000 сум» / «1 250 000 UZS» (bo‘linmaydigan bo‘sh joy bilan)."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    unit = CURRENCY.get((get_language() or "uz")[:2], CURRENCY["uz"])
    return f"{value:,}".replace(",", " ") + " " + unit
