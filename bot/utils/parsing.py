"""Parser input nominal rupiah yang ramah pengguna."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_NOMINAL_RE = re.compile(r"^(?P<num>\d[\d.,]*)\s*(?P<unit>ribu|rb|juta|jt|k)?$")


def parse_rupiah(text: object) -> Decimal:
    """Parse nominal: '500000', 'Rp500.000', '500rb', '1,5jt', '20k'.

    Raises:
        ValueError: bila teks bukan nominal yang bisa dipahami.
    """
    raw = str(text or "").strip().lower()
    raw = raw.replace("rp", "").replace("idr", "").replace(" ", "")
    if not raw:
        raise ValueError("Nominal belum diisi.")

    match = _NOMINAL_RE.match(raw)
    if not match:
        raise ValueError(f"Nominal '{text}' tidak valid.")

    num_str = match.group("num")
    unit = (match.group("unit") or "").lower()

    try:
        if unit:
            # Dengan satuan, satu pemisah + 1-2 digit di belakang dianggap
            # desimal (1,5jt / 1.5jt); selain itu pemisah ribuan.
            normalized = num_str.replace(",", ".")
            parts = normalized.split(".")
            if len(parts) > 2:
                normalized = normalized.replace(".", "")
            elif len(parts) == 2 and len(parts[1]) in (1, 2):
                pass
            else:
                normalized = normalized.replace(".", "")
            value = Decimal(normalized)
            value *= 1_000_000 if unit in ("jt", "juta") else 1_000
        else:
            # Tanpa satuan: titik dan koma dianggap pemisah ribuan.
            value = Decimal(num_str.replace(".", "").replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Nominal '{text}' tidak valid.") from exc

    if value < 0:
        raise ValueError("Nominal tidak boleh negatif.")
    return value
