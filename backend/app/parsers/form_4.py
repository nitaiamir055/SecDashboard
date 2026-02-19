"""Parser for SEC Form 4: insider transaction reporting (XML format)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET


TRANSACTION_CODES = {
    "P": "Purchase",
    "S": "Sale",
    "A": "Award/Grant",
    "D": "Disposition (non-open-market)",
    "F": "Payment of exercise price or tax liability",
    "I": "Discretionary transaction",
    "M": "Exercise or conversion of derivative security",
    "C": "Conversion of derivative security",
    "E": "Expiration of short derivative position",
    "G": "Gift",
    "L": "Small acquisition",
    "W": "Acquisition or disposition by will or laws of descent",
    "Z": "Deposit into or withdrawal from voting trust",
    "J": "Other acquisition or disposition",
}

RELATIONSHIP_MAP = {
    "isDirector": "Director",
    "isOfficer": "Officer",
    "isTenPercentOwner": "10% Owner",
    "isOther": "Other",
}


def _safe_text(el, path: str) -> str:
    """Safely extract text from an XML element."""
    node = el.find(path)
    return node.text.strip() if node is not None and node.text else ""


def _safe_float(el, path: str) -> float | None:
    text = _safe_text(el, path)
    try:
        return float(text.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def parse_form4(raw_xml: str) -> tuple[str, dict]:
    """Parse a Form 4 XML document. Returns (text_summary, parsed_data)."""
    # Some filings wrap XML in HTML; extract the XML portion
    xml_match = re.search(r"(<\?xml.*?</ownershipDocument>)", raw_xml, re.DOTALL)
    if xml_match:
        raw_xml = xml_match.group(1)

    # Try to parse as XML
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        # It's HTML (XSLT-rendered view) — extract text and try to find key data
        text = re.sub(r"<style[^>]*>.*?</style>", " ", raw_xml, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        # Try to extract transaction info from the rendered text
        data = {"parse_error": True}
        p_match = re.search(r"Purchase", text, re.IGNORECASE)
        s_match = re.search(r"Sale", text, re.IGNORECASE)
        if p_match:
            data["transaction_type"] = "P"
        elif s_match:
            data["transaction_type"] = "S"
        return (text[:4000], data)

    # Issuer info
    issuer_name = _safe_text(root, ".//issuerName")
    issuer_ticker = _safe_text(root, ".//issuerTradingSymbol")

    # Reporting owner info
    owner_name = _safe_text(root, ".//rptOwnerName")

    # Relationships
    relationships = []
    rel_el = root.find(".//reportingOwnerRelationship")
    if rel_el is not None:
        for tag, label in RELATIONSHIP_MAP.items():
            val = _safe_text(rel_el, tag)
            if val == "1" or val.lower() == "true":
                relationships.append(label)
        officer_title = _safe_text(rel_el, "officerTitle")
        if officer_title:
            relationships.append(f"Title: {officer_title}")

    # Non-derivative transactions
    transactions = []
    for txn in root.findall(".//nonDerivativeTransaction"):
        code = _safe_text(txn, ".//transactionCoding/transactionCode")
        shares = _safe_float(txn, ".//transactionAmounts/transactionShares/value")
        price = _safe_float(txn, ".//transactionAmounts/transactionPricePerShare/value")
        acquired_disposed = _safe_text(txn, ".//transactionAmounts/transactionAcquiredDisposedCode/value")
        post_shares = _safe_float(txn, ".//postTransactionAmounts/sharesOwnedFollowingTransaction/value")

        transactions.append({
            "code": code,
            "code_description": TRANSACTION_CODES.get(code, "Unknown"),
            "shares": shares,
            "price_per_share": price,
            "acquired_or_disposed": acquired_disposed,
            "shares_after": post_shares,
        })

    # Build summary text
    total_value = sum(
        (t["shares"] or 0) * (t["price_per_share"] or 0)
        for t in transactions
    )

    summary_parts = [
        f"Form 4: {owner_name} ({', '.join(relationships) if relationships else 'Unknown role'})",
        f"Issuer: {issuer_name} ({issuer_ticker})",
    ]
    for t in transactions:
        action = "bought" if t["code"] == "P" else "sold" if t["code"] == "S" else t["code_description"]
        shares_str = f"{t['shares']:,.0f}" if t["shares"] else "N/A"
        price_str = f"${t['price_per_share']:,.2f}" if t["price_per_share"] else "N/A"
        summary_parts.append(f"  {action} {shares_str} shares at {price_str}")

    text_summary = "\n".join(summary_parts)

    parsed_data = {
        "issuer_name": issuer_name,
        "issuer_ticker": issuer_ticker,
        "owner_name": owner_name,
        "relationships": relationships,
        "transactions": transactions,
        "total_transaction_value": total_value,
        "transaction_type": transactions[0]["code"] if transactions else None,
    }

    return (text_summary, parsed_data)
