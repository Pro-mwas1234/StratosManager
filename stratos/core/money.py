"""Money as integer cents (KES x100). Never use floats for arithmetic."""
from __future__ import annotations

VAT_RATE_DEFAULT = 0.16  # Kenya standard VAT


def parse_amount(value) -> int:
    """Accept int cents, numeric string '1200.50', or float (converted via str to avoid drift)."""
    if isinstance(value, bool):
        raise ValueError("invalid amount")
    if isinstance(value, int):
        return value
    s = str(value).strip().replace(",", "")
    if not s:
        raise ValueError("empty amount")
    neg = s.startswith("-")
    s = s.lstrip("+-")
    if "." in s:
        whole, frac = s.split(".", 1)
        frac = (frac + "00")[:3]  # look at 3rd digit for rounding
        cents = int(whole or "0") * 100 + int(frac[:2])
        if int(frac[2]) >= 5:
            cents += 1
    else:
        cents = int(s) * 100
    return -cents if neg else cents


def fmt_kes(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    c = abs(cents)
    return f"{sign}KES {c // 100:,}.{c % 100:02d}"


def vat_split(gross_or_net_cents: int, rate: float = VAT_RATE_DEFAULT, inclusive: bool = False):
    """Return (net, vat, gross) in cents. Half-up rounding on VAT."""
    if inclusive:
        net = round(gross_or_net_cents / (1 + rate))
        vat = gross_or_net_cents - net
        gross = gross_or_net_cents
    else:
        net = gross_or_net_cents
        vat = int(net * rate * 100 + 0.5) // 100 if net else 0
        vat = round(net * rate)
        gross = net + vat
    return net, vat, gross
