"""Load raw client files and map them into the standard transaction schema."""
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "data" / "reference"

# The schema is the single source of truth for column names and their order.
with open(ROOT / "config" / "schema.yaml", encoding="utf-8") as f:
    STANDARD_COLUMNS = list(yaml.safe_load(f)["transactions"]["columns"])

# A client's mapping must supply these. Everything else in the mapping is optional
# (see config/client_template.yaml) and is filled in when the client doesn't send it.
REQUIRED_MAPPED = ["invoice_id", "line_no", "transaction_type", "original_amount", "invoice_date"]
OPTIONAL_TEXT = ["original_supplier", "original_tax_code", "description",
                 "gst_charged", "original_destination"]


def _read_ref(name: str) -> pd.DataFrame:
    # keep_default_na=False so codes like "NA" (Namibia) aren't read as blanks
    return pd.read_csv(REF / name, dtype=str, keep_default_na=False)


def _to_money(value: str) -> Decimal | None:
    """Exact Decimal, never float. Blank or unusable -> None, for the quality checks to flag."""
    try:
        amount = Decimal(value.strip())
    except InvalidOperation:
        return None
    # Decimal parses "NaN" and "Infinity", which aren't amounts
    return amount if amount.is_finite() else None


def _to_int(value: str):
    try:
        return int(value.strip())
    except ValueError:
        return pd.NA


def load_mapping(path) -> dict:
    """Read a client mapping YAML file and return it as a dict."""
    with open(ROOT / path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_raw(mapping: dict) -> pd.DataFrame:
    """
    Read the client's raw CSV as strings (dtype=str, keep_default_na=False).
    Add client_id, source_file and source_row_number (1 = first data row).
    """
    path = ROOT / mapping["file"]
    # utf-8-sig also accepts the byte order mark Excel adds to the first column name
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df["client_id"] = mapping["client_id"]
    df["source_file"] = path.name
    df["source_row_number"] = range(1, len(df) + 1)
    return df


def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    Check every raw column in the mapping exists. If any are missing, raise a
    ValueError that names them (fail loudly, don't guess).
    Rename the columns, then apply value_maps.

    Values with no entry in value_maps are kept as received rather than blanked,
    so an unrecognised code is never mistaken for a missing one.
    """
    client = mapping["client_id"]

    missing_raw = [raw for raw in mapping["columns"] if raw not in df.columns]
    if missing_raw:
        raise ValueError(f"{client}: raw columns in the mapping are missing from the file: {missing_raw}")

    unmapped = [col for col in REQUIRED_MAPPED if col not in mapping["columns"].values()]
    if unmapped:
        raise ValueError(f"{client}: mapping has no raw column for required columns: {unmapped}")

    df = df.rename(columns=mapping["columns"])

    for col, values in mapping.get("value_maps", {}).items():
        if col in df.columns:
            df[col] = df[col].map(lambda v: values.get(v.strip(), v))
    return df


def standardise(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    - invoice_date: parse with the client's date_format; unparseable -> NaT (don't crash)
    - tax_code: original_tax_code trimmed and upper case
    - destination_country: original_destination trimmed and upper case,
      blank if not in countries.csv
    - supplier_id: look up original_supplier in suppliers.csv by name, blank if no match
    - original_amount, gst_charged: convert to Decimal, None if blank
    - line_no: integer
    - amounts_include_gst: from the mapping

    Optional columns the client doesn't send are added as blank, and a blank or
    absent document_type defaults to invoice, so every client has the same columns.
    Returns the columns in schema order.
    """
    df = df.copy()

    for col in OPTIONAL_TEXT:
        if col not in df.columns:
            df[col] = ""
    if "document_type" not in df.columns:
        df["document_type"] = ""
    df["document_type"] = df["document_type"].where(df["document_type"].str.strip() != "", "invoice")

    df["invoice_date"] = pd.to_datetime(
        df["invoice_date"].str.strip(), format=mapping["date_format"], errors="coerce"
    )
    df["tax_code"] = df["original_tax_code"].str.strip().str.upper()

    destination = df["original_destination"].str.strip().str.upper()
    valid_country = destination.isin(_read_ref("countries.csv")["country_code"])
    df["destination_country"] = destination.where(valid_country, "")

    suppliers = _read_ref("suppliers.csv")
    supplier_ids = dict(zip(suppliers["supplier_name"], suppliers["supplier_id"]))
    df["supplier_id"] = df["original_supplier"].map(lambda name: supplier_ids.get(name.strip(), ""))

    # Built as object columns explicitly, so pandas can't coerce the Decimals to float
    for col in ["original_amount", "gst_charged"]:
        df[col] = pd.Series([_to_money(v) for v in df[col]], index=df.index, dtype=object)

    # Int64 (not int) so a blank or malformed line number can be held as <NA>
    df["line_no"] = pd.array([_to_int(v) for v in df["line_no"]], dtype="Int64")

    df["amounts_include_gst"] = mapping["amounts_include_gst"]

    return df[STANDARD_COLUMNS]


def ingest_client(mapping_path) -> pd.DataFrame:
    """Run the three steps above for one client."""
    mapping = load_mapping(mapping_path)
    return standardise(apply_mapping(read_raw(mapping), mapping), mapping)


def ingest_all(mapping_paths) -> pd.DataFrame:
    """Ingest every client and stack them into one DataFrame."""
    return pd.concat([ingest_client(path) for path in mapping_paths], ignore_index=True)
