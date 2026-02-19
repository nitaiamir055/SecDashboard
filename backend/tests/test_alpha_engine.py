"""Tests for the heuristic alpha engine."""

from app.services.alpha_engine import pre_classify


def test_catalyst_bullish():
    assert pre_classify("catalyst", {"items": ["1.01", "9.01"]}) == "bullish"


def test_catalyst_bearish():
    assert pre_classify("catalyst", {"items": ["5.02", "9.01"]}) == "bearish"


def test_catalyst_neutral():
    assert pre_classify("catalyst", {"items": ["8.01"]}) == "neutral"


def test_insider_purchase():
    assert pre_classify("insider", {"transaction_type": "P"}) == "bullish"


def test_insider_sale():
    assert pre_classify("insider", {"transaction_type": "S"}) == "bearish"


def test_dilution_always_bearish():
    assert pre_classify("dilution", {}) == "bearish"


def test_whale_13d():
    assert pre_classify("whale", {"form_subtype": "13D"}) == "bullish"


def test_whale_passive():
    assert pre_classify("whale", {"form_subtype": "13G", "strategy": "passive"}) == "neutral"


def test_pulse_positive():
    assert pre_classify("pulse", {"sentiment_score": 2}) == "bullish"


def test_pulse_negative():
    assert pre_classify("pulse", {"sentiment_score": -3}) == "bearish"
