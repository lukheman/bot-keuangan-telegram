"""Test persistensi pending transaksi (UX-021/UX-026)."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.models import TransactionType
from app.services.pending_service import (
    deserialize_pending,
    is_expired,
    serialize_pending,
)


def _pending():
    return {
        "user": SimpleNamespace(id=123456, username="akmal", full_name="Akmal"),
        "kind": "simple",
        "amount": Decimal("20000"),
        "description": "kopi",
        "type": TransactionType.EXPENSE,
        "category": "Makanan",
        "wallet_name": None,
        "confidence": 0.5,
        "needs_preview": True,
    }


def test_serialize_pending_bisa_disimpan_sebagai_json():
    payload = serialize_pending(_pending())

    # Tidak boleh ada objek Telegram/Decimal yang gagal di-JSON-kan.
    encoded = json.dumps(payload)
    assert "akmal" in encoded
    assert payload["amount"] == "20000"
    assert payload["type"] == "EXPENSE"
    assert payload["user"]["id"] == 123456


def test_deserialize_pending_mengembalikan_tipe_asli():
    pending = deserialize_pending(serialize_pending(_pending()))

    assert pending["amount"] == Decimal("20000")
    assert pending["type"] == TransactionType.EXPENSE
    assert pending["user"].id == 123456
    assert pending["user"].full_name == "Akmal"
    assert pending["needs_preview"] is True


def test_is_expired_aman_untuk_datetime_naive():
    now = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

    assert is_expired(now - timedelta(seconds=1), now)
    assert not is_expired(now + timedelta(seconds=1), now)
    # SQLite mengembalikan datetime tanpa timezone.
    naive = datetime(2026, 11, 12, 11, 59)
    assert is_expired(naive, now)
