"""Tests for the form parsers."""

from app.parsers.form_8k import parse_8k
from app.parsers.form_4 import parse_form4
from app.parsers.form_s1_s3 import parse_s1_s3
from app.parsers.form_13d_13g import parse_13d_13g
from app.parsers.form_10q import parse_10q


def test_parse_8k(sample_8k_html):
    text, data = parse_8k(sample_8k_html)
    assert "1.01" in data["items"]
    assert "9.01" in data["items"]
    assert data["has_bullish_items"] is True
    assert "Acme" in text


def test_parse_form4(sample_form4_xml):
    text, data = parse_form4(sample_form4_xml)
    assert data["issuer_ticker"] == "ACME"
    assert data["owner_name"] == "John Smith"
    assert len(data["transactions"]) == 1
    txn = data["transactions"][0]
    assert txn["code"] == "P"
    assert txn["shares"] == 10000.0
    assert txn["price_per_share"] == 25.50
    assert txn["shares_after"] == 150000.0
    assert data["total_transaction_value"] == 255000.0
    assert "Officer" in data["relationships"]


def test_parse_s1_s3():
    html = """<html><body>
    <p>The company is offering 5,000,000 shares of common stock at a
    price of $10.00 per share for a total offering of $50 million.</p>
    <p>Use of proceeds: The company intends to use the net proceeds for
    general corporate purposes, including working capital and research
    and development.</p>
    </body></html>"""
    text, data = parse_s1_s3(html)
    assert data["proposed_shares"] == 5000000.0
    assert "working_capital" in data["use_of_proceeds"]
    assert "growth" in data["use_of_proceeds"]


def test_parse_13d():
    html = """<html><body>
    <p>SCHEDULE 13D</p>
    <p>NAME OF REPORTING PERSON: Icahn Enterprises</p>
    <p>The reporting person owns 8.5% of the outstanding shares.</p>
    <p>Item 4. PURPOSE OF TRANSACTION</p>
    <p>The reporting person intends to seek board seats and explore
    strategic alternatives to maximize shareholder value.</p>
    <p>Item 5. Interest in Securities</p>
    </body></html>"""
    text, data = parse_13d_13g(html)
    assert data["form_subtype"] == "13D"
    assert data["ownership_pct"] == 8.5
    assert data["strategy"] == "activist"
    assert data["has_activism_language"] is True


def test_parse_10q():
    html = """<html><body>
    <p>Total revenue: $1,250,000</p>
    <p>Net income: $125,000</p>
    <p>Basic earnings per share: $2.50</p>
    <p>Cash and cash equivalents: $500,000</p>
    <p>Management's Discussion and Analysis</p>
    <p>We experienced strong demand for our products during the quarter.
    Revenue growth was driven by expansion into new markets. However,
    supply chain disruptions and inflation pressures continue to
    impact our operating margins. We also face uncertainty regarding
    regulatory changes that may affect our operations.</p>
    </body></html>"""
    text, data = parse_10q(html)
    assert data["revenue"] == 1250000.0
    assert data["net_income"] == 125000.0
    assert data["eps"] == 2.50
    assert data["cash_and_equivalents"] == 500000.0
    assert "supply chain" in data["risk_mentions"]
    assert "strong demand" in data["positive_mentions"]
