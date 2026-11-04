"""Check the reference tables only use values the schema allows."""
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = yaml.safe_load(open(ROOT / "config" / "schema.yaml", encoding="utf-8"))
VALID_CATEGORIES = set(SCHEMA["enums"]["category"])


def read_ref(name):
    # keep_default_na=False so codes like "NA" (Namibia) aren't read as blanks
    return pd.read_csv(ROOT / "data" / "reference" / name, keep_default_na=False)


def test_tax_code_categories_are_valid():
    bad = set(read_ref("tax_codes.csv")["category"]) - VALID_CATEGORIES
    assert not bad, f"Unknown categories in tax_codes.csv: {bad}"


def test_supplier_default_categories_are_valid():
    defaults = set(read_ref("suppliers.csv")["default_category"]) - {""}
    bad = defaults - VALID_CATEGORIES
    assert not bad, f"Unknown categories in suppliers.csv: {bad}"
