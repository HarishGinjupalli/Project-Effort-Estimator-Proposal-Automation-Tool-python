"""Unit tests for utils.py"""

from src.utils import format_currency, _indian_grouping


def test_format_currency_inr():
    assert format_currency(1234567.5, "INR") == "₹12,34,567.50"


def test_format_currency_usd():
    assert format_currency(1234.5, "USD") == "USD 1,234.50"


def test_indian_grouping_small_number():
    assert _indian_grouping(999.99) == "999.99"


def test_indian_grouping_negative():
    assert _indian_grouping(-1234567.5) == "-12,34,567.50"
