"""Check the data quality checks against the planted errors and edge cases."""
from decimal import Decimal

import pandas as pd

from gst_engine.ingest import ingest_all
from gst_engine.quality import ISSUE_COLUMNS, check_amount_outliers

MAPPINGS = ["config/client_a_mapping.yaml", "config/client_b_mapping.yaml"]
GROUP = ["client_id", "supplier_id"]


def lines(amounts, supplier_id="S05"):
    """A tiny handmade set of invoice lines. S05 is single-category, S01 is multi-category."""
    return pd.DataFrame({
        "client_id": "client_t",
        "source_file": "t.csv",
        "source_row_number": range(1, len(amounts) + 1),
        "invoice_id": [f"{supplier_id}-{n}" for n in range(1, len(amounts) + 1)],
        "line_no": 1,
        "supplier_id": supplier_id,
        "document_type": "invoice",
        "original_amount": [Decimal(a) for a in amounts],
    })


def test_outliers_on_real_data_are_exactly_the_planted_rows():
    issues = check_amount_outliers(ingest_all(MAPPINGS), "original_amount", GROUP)

    assert list(issues.columns) == ISSUE_COLUMNS
    found = sorted(zip(issues["invoice_id"], issues["line_no"]))
    assert found == [("A-INV-0010", 1), ("A-INV-0010", 2), ("B-INV-0013", 1)]
    assert set(issues["check_name"]) == {"amount_outlier"}
    assert set(issues["severity"]) == {"info"}


def test_supplier_with_identical_amounts_is_not_flagged():
    issues = check_amount_outliers(lines(["100.00"] * 5), "original_amount", GROUP)

    assert issues.empty
    assert list(issues.columns) == ISSUE_COLUMNS


def test_negative_amount_is_not_flagged():
    df = lines(["100.00", "101.00", "102.00", "103.00", "104.00", "-5000.00"])
    assert check_amount_outliers(df, "original_amount", GROUP).empty


def test_unusually_small_amount_is_not_flagged():
    df = lines(["100.00", "101.00", "102.00", "103.00", "104.00", "1.00"])
    assert check_amount_outliers(df, "original_amount", GROUP).empty


def test_multi_category_supplier_with_huge_amount_is_not_flagged():
    amounts = ["100.00", "101.00", "102.00", "103.00", "104.00", "99999.00"]
    df = pd.concat([lines(amounts, supplier_id="S01"), lines(amounts, supplier_id="S05")], ignore_index=True)

    issues = check_amount_outliers(df, "original_amount", GROUP)

    # The same amounts on single-category S05 are flagged, so only S01's status differs
    assert issues["invoice_id"].tolist() == ["S05-6"]
