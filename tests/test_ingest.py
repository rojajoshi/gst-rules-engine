"""Check raw client files land in the standard schema, with bad values kept visible."""
from decimal import Decimal

import pandas as pd
import pytest
import yaml

from gst_engine.ingest import ROOT, apply_mapping, ingest_all, ingest_client, load_mapping, read_raw

MAPPINGS = ["config/client_a_mapping.yaml", "config/client_b_mapping.yaml"]
SCHEMA = yaml.safe_load(open(ROOT / "config" / "schema.yaml", encoding="utf-8"))


@pytest.fixture(scope="module")
def txns():
    return ingest_all(MAPPINGS)


def line(txns, invoice_id, line_no):
    """First row for an invoice line."""
    rows = txns[(txns["invoice_id"] == invoice_id) & (txns["line_no"] == line_no)]
    assert len(rows) >= 1, f"{invoice_id} line {line_no} not found"
    return rows.iloc[0]


def write_client(tmp_path, csv_text, **overrides):
    """A small throwaway client, for cases the generated data doesn't contain."""
    raw = tmp_path / "raw.csv"
    raw.write_text(csv_text, encoding="utf-8")
    config = {
        "client_id": "client_t",
        "file": str(raw),
        "amounts_include_gst": False,
        "date_format": "%Y-%m-%d",
        "columns": {"id": "invoice_id", "ln": "line_no", "ty": "transaction_type",
                    "amt": "original_amount", "dt": "invoice_date"},
        "value_maps": {"transaction_type": {"S": "sale", "P": "purchase"}},
    }
    config.update(overrides)
    path = tmp_path / "mapping.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_columns_match_schema_in_order(txns):
    assert list(txns.columns) == list(SCHEMA["transactions"]["columns"])


def test_every_raw_row_is_kept_including_duplicates(txns):
    assert (txns["client_id"] == "client_a").sum() == 148
    assert (txns["client_id"] == "client_b").sum() == 162
    copies = txns[(txns["invoice_id"] == "A-INV-0001") & (txns["line_no"] == 1)]
    assert len(copies) == 2


def test_source_columns_trace_back_to_the_raw_file(txns):
    b = txns[txns["client_id"] == "client_b"]
    assert b["source_file"].unique().tolist() == ["client_b.csv"]
    assert b["source_row_number"].tolist() == list(range(1, 163))
    # Row 6 of client_b.csv is the planted 31 February
    assert b.iloc[5]["invoice_id"] == "B-INV-0002" and b.iloc[5]["source_row_number"] == 6


def test_value_maps_applied(txns):
    assert set(txns["document_type"]) == {"invoice", "credit_note"}
    assert set(txns["transaction_type"]) == {"sale", "purchase"}
    assert line(txns, "A-INV-0007", 1)["document_type"] == "credit_note"


def test_dates_use_each_clients_format(txns):
    assert line(txns, "A-INV-0001", 1)["invoice_date"] == pd.Timestamp("2026-07-09")
    # 01/09/2026 is 1 September for Client B, not 9 January
    assert line(txns, "B-INV-0001", 1)["invoice_date"] == pd.Timestamp("2026-09-01")


def test_impossible_date_becomes_nat_without_crashing(txns):
    assert pd.isna(line(txns, "B-INV-0002", 4)["invoice_date"])
    assert txns["invoice_date"].isna().sum() == 1


def test_money_is_exact_decimal_and_blank_is_none(txns):
    row = line(txns, "A-INV-0001", 1)
    assert isinstance(row["original_amount"], Decimal) and row["original_amount"] == Decimal("192.50")
    assert isinstance(row["gst_charged"], Decimal)
    assert line(txns, "A-INV-0011", 1)["original_amount"] == Decimal("-45.00")
    assert line(txns, "B-INV-0005", 2)["original_amount"] is None


def test_amounts_include_gst_comes_from_the_mapping(txns):
    assert not txns.loc[txns["client_id"] == "client_a", "amounts_include_gst"].any()
    assert txns.loc[txns["client_id"] == "client_b", "amounts_include_gst"].all()


def test_supplier_lookup(txns):
    assert line(txns, "A-INV-0001", 1)["supplier_id"] == "S04"
    orphan = line(txns, "A-INV-0010", 3)
    assert orphan["original_supplier"] == "Mystery Traders Pty Ltd" and orphan["supplier_id"] == ""
    assert line(txns, "A-INV-0022", 1)["supplier_id"] == ""


def test_unmapped_tax_code_is_kept_for_the_quality_check(txns):
    assert line(txns, "B-INV-0026", 1)["tax_code"] == "ZZ"
    assert line(txns, "A-INV-0004", 1)["tax_code"] == ""


def test_invalid_country_goes_blank_so_it_cannot_become_an_export(txns):
    row = line(txns, "A-INV-0014", 2)
    assert row["original_destination"] == "Australia" and row["destination_country"] == ""
    assert line(txns, "A-INV-0012", 2)["destination_country"] == ""


def test_values_are_normalised_but_originals_are_untouched(tmp_path):
    path = write_client(
        tmp_path,
        "id,ln,ty,amt,dt,code,dest\nX1,1,S,10.00,2026-07-01, st ,nz \nX2,1,S,10.00,2026-07-01,,NA\n",
        columns={"id": "invoice_id", "ln": "line_no", "ty": "transaction_type", "amt": "original_amount",
                 "dt": "invoice_date", "code": "original_tax_code", "dest": "original_destination"},
    )
    df = ingest_client(path)
    assert df.loc[0, "tax_code"] == "ST" and df.loc[0, "original_tax_code"] == " st "
    assert df.loc[0, "destination_country"] == "NZ" and df.loc[0, "original_destination"] == "nz "
    # NA is Namibia, not a missing value
    assert df.loc[1, "destination_country"] == "NA"


def test_optional_columns_can_be_left_out_of_the_mapping(tmp_path):
    df = ingest_client(write_client(tmp_path, "id,ln,ty,amt,dt\nX1,1,P,10.00,2026-07-01\n"))
    assert list(df.columns) == list(SCHEMA["transactions"]["columns"])
    row = df.iloc[0]
    assert row["document_type"] == "invoice"
    assert row["original_supplier"] == "" and row["supplier_id"] == ""
    assert row["tax_code"] == "" and row["destination_country"] == ""
    assert row["gst_charged"] is None


def test_unrecognised_mapped_value_is_kept_not_blanked(tmp_path):
    df = ingest_client(write_client(tmp_path, "id,ln,ty,amt,dt\nX1,1,Z,10.00,2026-07-01\n"))
    assert df.loc[0, "transaction_type"] == "Z"


def test_bad_row_values_do_not_stop_the_file(tmp_path):
    csv_text = "id,ln,ty,amt,dt\nX1,abc,P,\"1,000.00\",nope\nX2,,P,NaN,\nX3,2,P,10.00,2026-07-01\n"
    df = ingest_client(write_client(tmp_path, csv_text))
    assert len(df) == 3
    assert df["line_no"].isna().tolist() == [True, True, False]
    assert df["original_amount"].tolist() == [None, None, Decimal("10.00")]
    assert df["invoice_date"].isna().tolist() == [True, True, False]


def test_missing_raw_column_fails_loudly_and_names_it():
    mapping = load_mapping(MAPPINGS[0])
    raw = read_raw(mapping).drop(columns=["NetAmt", "ShipTo"])
    with pytest.raises(ValueError, match=r"NetAmt.*ShipTo"):
        apply_mapping(raw, mapping)


def test_mapping_without_a_required_column_fails_loudly(tmp_path):
    path = write_client(
        tmp_path, "id,ln,ty,amt,dt\nX1,1,P,10.00,2026-07-01\n",
        columns={"id": "invoice_id", "ln": "line_no", "ty": "transaction_type", "dt": "invoice_date"},
    )
    with pytest.raises(ValueError, match="original_amount"):
        ingest_client(path)
