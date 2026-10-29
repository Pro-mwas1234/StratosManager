"""Unit tests for core primitives: money math, validation, password hashing."""
import pytest

from stratos.core.money import VAT_RATE_DEFAULT, fmt_kes, parse_amount, vat_split
from stratos.core.domain import hash_password, verify_password, validate_kra_pin, normalize_phone
from stratos.core.errors import ValidationError


class TestMoney:
    @pytest.mark.parametrize("raw,cents", [
        (100, 100),            # already cents
        ("100", 10_000),       # whole shillings string
        ("1200.50", 120_050),
        ("1,200.50", 120_050),  # thousands separators
        ("0.999", 100),         # third-digit rounding half-up
        ("-5.25", -525),
    ])
    def test_parse(self, raw, cents):
        assert parse_amount(raw) == cents

    def test_no_float_drift(self):
        # classic float trap: 1.005 must not silently become 100.49999...
        assert parse_amount(1.005) == 101 or parse_amount(str(1.005)) == 100

    def test_fmt(self):
        assert fmt_kes(12_3456) == "KES 1,234.56"
        assert fmt_kes(-500) == "-KES 5.00"

    def test_vat_exclusive_roundtrip(self):
        net, vat, gross = vat_split(100_000)  # KES 1000 + 16%
        assert (net, vat, gross) == (100_000, 16_000, 116_000)

    def test_vat_inclusive(self):
        net, vat, gross = vat_split(116_000, VAT_RATE_DEFAULT, inclusive=True)
        assert gross == 116_000 and net + vat == gross and net == 100_000

    def test_rejects_bool(self):
        with pytest.raises(ValueError):
            parse_amount(True)


class TestDomainValidators:
    def test_kra_ok(self):
        assert validate_kra_pin("a123456789z") == "A123456789Z"

    @pytest.mark.parametrize("bad", ["12345678", "A12345", "X123456789Z"])
    def test_kra_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_kra_pin(bad)

    def test_kra_none_passthrough(self):
        assert validate_kra_pin(None) is None and validate_kra_pin("") is None

    @pytest.mark.parametrize("raw,want", [
        ("0712345678", "+254712345678"),
        ("+254712345678", "+254712345678"),
        ("254712345678", "+254712345678"),
    ])
    def test_phone(self, raw, want):
        assert normalize_phone(raw) == want

    def test_password_roundtrip(self):
        h = hash_password("s3cret-pass")
        assert h.startswith("pbkdf2$")
        assert verify_password("s3cret-pass", h)
        assert not verify_password("wrong", h)
