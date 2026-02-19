import pytest


@pytest.fixture
def sample_8k_html():
    return """<html><body>
    <h1>FORM 8-K</h1>
    <p>Item 1.01 - Entry into a Material Definitive Agreement</p>
    <p>On February 15, 2026, Acme Corp entered into a definitive agreement
    to acquire Widget Inc for $500 million in cash. The acquisition is
    expected to close in Q2 2026.</p>
    <p>Item 9.01 - Financial Statements and Exhibits</p>
    </body></html>"""


@pytest.fixture
def sample_form4_xml():
    return """<?xml version="1.0"?>
    <ownershipDocument>
        <issuer>
            <issuerCik>0001234567</issuerCik>
            <issuerName>Acme Corp</issuerName>
            <issuerTradingSymbol>ACME</issuerTradingSymbol>
        </issuer>
        <reportingOwner>
            <reportingOwnerId>
                <rptOwnerCik>0009876543</rptOwnerCik>
                <rptOwnerName>John Smith</rptOwnerName>
            </reportingOwnerId>
            <reportingOwnerRelationship>
                <isDirector>0</isDirector>
                <isOfficer>1</isOfficer>
                <isTenPercentOwner>0</isTenPercentOwner>
                <isOther>0</isOther>
                <officerTitle>CEO</officerTitle>
            </reportingOwnerRelationship>
        </reportingOwner>
        <nonDerivativeTable>
            <nonDerivativeTransaction>
                <transactionCoding>
                    <transactionCode>P</transactionCode>
                </transactionCoding>
                <transactionAmounts>
                    <transactionShares><value>10000</value></transactionShares>
                    <transactionPricePerShare><value>25.50</value></transactionPricePerShare>
                    <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
                </transactionAmounts>
                <postTransactionAmounts>
                    <sharesOwnedFollowingTransaction><value>150000</value></sharesOwnedFollowingTransaction>
                </postTransactionAmounts>
            </nonDerivativeTransaction>
        </nonDerivativeTable>
    </ownershipDocument>"""
