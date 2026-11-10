"""Data quality checks: each one returns rows in the standard issues format."""
import numpy as np
import pandas as pd
import yaml

from gst_engine.ingest import ROOT, _read_ref

with open(ROOT / "config" / "schema.yaml", encoding="utf-8") as f:
    ISSUE_COLUMNS = list(yaml.safe_load(f)["issues"]["columns"])


def _issues(rows: pd.DataFrame, check_name: str, severity: str, messages) -> pd.DataFrame:
    """Build one issue per row. messages is a single string or one string per row."""
    issues = rows.assign(check_name=check_name, severity=severity, message=messages)
    return issues[ISSUE_COLUMNS].reset_index(drop=True)


def check_amount_outliers(df: pd.DataFrame, amount_col: str, group_col, threshold: float = 3.5) -> pd.DataFrame:
    """
    Flag amounts unusually high for their group, using the modified z-score:
    0.6745 * (amount - median) / MAD. Median and MAD aren't dragged around by the
    outliers themselves, which a mean and standard deviation would be.

    Skips missing, zero and negative amounts, blank supplier_id, credit notes and
    multi-category suppliers. A group with a MAD of 0 has no usable spread, so it
    gets no score and is never flagged.
    """
    suppliers = _read_ref("suppliers.csv")
    multi = set(suppliers.loc[suppliers["multi_category"] == "True", "supplier_id"])

    # Float is fine here: this is a statistic for flagging, not a money calculation.
    # A missing amount becomes NaN, which also fails the > 0 test.
    amounts = df[amount_col].astype(float)
    rows = df[
        (amounts > 0)
        & (df["supplier_id"] != "")
        & (df["document_type"] != "credit_note")
        & ~df["supplier_id"].isin(multi)
    ].copy()

    rows["_amount"] = amounts[rows.index]
    median = rows.groupby(group_col)["_amount"].transform("median")
    rows["_deviation"] = (rows["_amount"] - median).abs()
    mad = rows.groupby(group_col)["_deviation"].transform("median")

    # NaN scores compare False against the threshold, so MAD = 0 can't be flagged
    score = 0.6745 * (rows["_amount"] - median) / mad.replace(0, np.nan)
    is_outlier = score > threshold

    flagged = rows[is_outlier]
    messages = [
        f"Amount {amount} is unusual for this supplier: modified z-score {z:.1f} (group median {med:.2f})"
        for amount, z, med in zip(flagged[amount_col], score[is_outlier], median[is_outlier])
    ]
    return _issues(flagged, "amount_outlier", "info", messages)
