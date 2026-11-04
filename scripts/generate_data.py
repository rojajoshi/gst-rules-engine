"""
Generate synthetic client data for the GST rules engine.

Creates:
  data/reference/suppliers.csv     fictional suppliers
  data/reference/tax_codes.csv     tax code -> category mapping
  data/raw/client_a.csv            Client A export (GST-exclusive amounts)
  data/raw/client_b.csv            Client B export (GST-inclusive amounts)
  data/reference/planted_errors.csv  every deliberate problem and the check that should catch it

All data is synthetic. Supplier names are made up.
Run from the repo root:  python scripts/generate_data.py
"""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"
rng = np.random.default_rng(42)  # fixed seed: same data every run

CENT = Decimal("0.01")


def money(x) -> Decimal:
    """Round to cents using round half up (the ATO convention)."""
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
SUPPLIERS = pd.DataFrame([
    # supplier_id, supplier_name, default_category, multi_category, gst_registered, country
    ("S01", "Fresh Fields Grocers",       "basic_food",         True,  True,  "AU"),
    ("S02", "Brew & Bite Cafe",           "taxable_food",       False, True,  "AU"),
    ("S03", "Northbridge Bank",           "financial_services", False, True,  "AU"),
    ("S04", "Riverside Medical Clinic",   "gst_free_medical",   False, True,  "AU"),
    ("S05", "PaperTrail Office Supplies", "stationery",         False, True,  "AU"),
    ("S06", "CloudForge Software",        "software",           False, True,  "AU"),
    ("S07", "Swift Payments",             "payment_processing", False, True,  "AU"),
    ("S08", "Corner Print Shop",          "stationery",         False, False, "AU"),  # NOT GST-registered
], columns=["supplier_id", "supplier_name", "default_category",
            "multi_category", "gst_registered", "country"])

TAX_CODES = pd.DataFrame([
    ("ST", "stationery", "Office supplies and printing"),
    ("SW", "software", "Software and licences"),
    ("TF", "taxable_food", "Prepared, hot or other taxable food"),
    ("BF", "basic_food", "GST-free basic food"),
    ("FS", "financial_services", "Input-taxed financial supplies"),
    ("PP", "payment_processing", "Payment processing (taxable)"),
    ("MED", "gst_free_medical", "GST-free medical services"),
    ("OHS", "gst_free_other_health", "GST-free other health services"),
    ("COS", "cosmetic_procedure", "Cosmetic procedures (taxable)"),
], columns=["tax_code", "category", "description"])

CODE_FOR = dict(zip(TAX_CODES.category, TAX_CODES.tax_code))
NAME_FOR = dict(zip(SUPPLIERS.supplier_id, SUPPLIERS.supplier_name))
REGISTERED = dict(zip(SUPPLIERS.supplier_id, SUPPLIERS.gst_registered))

TAXABLE = {"stationery", "software", "taxable_food", "payment_processing", "cosmetic_procedure"}

# Typical GST-exclusive amount range for each category (min, max)
AMOUNT_RANGE = {
    "basic_food": (20, 150), "taxable_food": (15, 60), "financial_services": (10, 500),
    "gst_free_medical": (60, 250), "stationery": (20, 300), "software": (300, 2000),
    "payment_processing": (20, 200),
}

DESCRIPTIONS = {
    "basic_food": ["Full cream milk 2L", "Fresh bananas 1kg", "Wholemeal bread loaf",
                   "Free range eggs 12pk", "Cold cooked chicken", "Brown rice 5kg"],
    "taxable_food": ["Hot roast chicken", "Flat white x10", "Catering platter",
                     "Chocolate biscuits", "Soft drink carton"],
    "financial_services": ["Loan interest", "Account keeping fee", "Overdraft interest"],
    "gst_free_medical": ["GP consultation", "Pathology tests"],
    "stationery": ["A4 paper 5 reams", "Printer toner", "Whiteboard markers", "Business cards printing"],
    "software": ["Accounting software licence", "Cloud storage annual plan", "Design software seat"],
    "payment_processing": ["Merchant service fee", "Card terminal fee"],
}

# Which suppliers each client buys from, and which categories each client sells
PURCHASE_SUPPLIERS = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"]
SALE_CATEGORIES = ["stationery", "software", "taxable_food", "basic_food"]
EXPORT_COUNTRIES = ["NZ", "JP", "US", "SG"]


def random_amount(category: str) -> Decimal:
    lo, hi = AMOUNT_RANGE[category]
    return money(rng.uniform(lo, hi))


def random_date() -> pd.Timestamp:
    """A date in Q3 2026 (Jul to Sep)."""
    return pd.Timestamp("2026-07-01") + pd.Timedelta(days=int(rng.integers(0, 92)))


def make_lines(client: str, n_invoices: int) -> list[dict]:
    """
    Build clean invoice lines in a neutral internal format.
    Each client's writer below converts these into that client's own column names.
    """
    lines = []
    prefix = "A" if client == "client_a" else "B"
    for i in range(1, n_invoices + 1):
        invoice_id = f"{prefix}-INV-{i:04d}"
        date = random_date()
        is_sale = rng.random() < 0.4
        n_lines = int(rng.integers(1, 5))

        if is_sale:
            supplier_id = ""  # on a sale, the client is the supplier
            destination = rng.choice(EXPORT_COUNTRIES) if rng.random() < 0.08 else "AU"
        else:
            supplier_id = rng.choice(PURCHASE_SUPPLIERS)
            destination = "AU"

        for line_no in range(1, n_lines + 1):
            if is_sale:
                category = rng.choice(SALE_CATEGORIES)
            else:
                # The supermarket (S01) sells several categories; others sell their default
                if supplier_id == "S01":
                    category = rng.choice(["basic_food", "taxable_food"])
                else:
                    category = SUPPLIERS.set_index("supplier_id").at[supplier_id, "default_category"]

            net = random_amount(category)
            charges_gst = category in TAXABLE and destination == "AU"
            if not is_sale and not REGISTERED[supplier_id]:
                charges_gst = False  # unregistered suppliers can't charge GST
            gst = money(net * Decimal("0.10")) if charges_gst else Decimal("0.00")

            lines.append({
                "invoice_id": invoice_id, "line_no": line_no, "date": date,
                "doc_type": "invoice", "txn_type": "sale" if is_sale else "purchase",
                "supplier_id": supplier_id, "tax_code": CODE_FOR[category],
                "description": rng.choice(DESCRIPTIONS[category]),
                "net": net, "gst": gst, "destination": destination,
            })
    return lines


# ---------------------------------------------------------------------------
# Planted errors. Every one is recorded so tests know exactly what to expect.
# ---------------------------------------------------------------------------
planted = []


def plant(client, invoice_id, line_no, check, note):
    planted.append({"client_id": client, "invoice_id": invoice_id, "line_no": line_no,
                    "expected_check": check, "note": note})


def find(lines, **conditions):
    """First line matching all conditions (e.g. txn_type='purchase', supplier_id='S05')."""
    return next(l for l in lines if all(l[k] == v for k, v in conditions.items()))


def plant_client_a(lines):
    c = "client_a"

    # 1. Outliers: two stationery purchases far above normal for PaperTrail (S05)
    s05 = [l for l in lines if l["supplier_id"] == "S05"]
    for line, amount in zip(s05[:2], ["9500.00", "12000.00"]):
        line["net"] = Decimal(amount)
        line["gst"] = money(line["net"] * Decimal("0.10"))
        plant(c, line["invoice_id"], line["line_no"], "amount_outlier",
              "Unusually large for this supplier. Flag as info, not invalid")

    # 2. Negative amount on a normal invoice (suspicious)
    line = find(lines, txn_type="purchase", supplier_id="S02")
    line["net"], line["gst"] = Decimal("-45.00"), Decimal("-4.50")
    plant(c, line["invoice_id"], line["line_no"], "negative_amount_on_invoice",
          "Negative on an invoice")

    # 3. Negative amount on a credit note (legitimate, must NOT be flagged)
    line = find(lines, txn_type="purchase", supplier_id="S06")
    line["doc_type"] = "credit_note"
    line["net"], line["gst"] = Decimal("-150.00"), Decimal("-15.00")
    plant(c, line["invoice_id"], line["line_no"], "none",
          "Credit note refund. Negative is valid, should not be flagged")

    # 4. Wrong GST charged ($3 too much)
    line = find(lines, txn_type="purchase", supplier_id="S07")
    line["gst"] += Decimal("3.00")
    plant(c, line["invoice_id"], line["line_no"], "gst_mismatch", "GST overcharged by $3.00")

    # 5. Unregistered supplier (S08) showing GST
    line = find(lines, supplier_id="S08")
    line["gst"] = money(line["net"] * Decimal("0.10"))
    plant(c, line["invoice_id"], line["line_no"], "gst_charged_by_unregistered_supplier",
          "Corner Print Shop isn't GST-registered but charged GST")

    # 6. Orphan supplier: name not in suppliers.csv
    line = s05[2]  # a PaperTrail line that isn't one of the outliers
    line["supplier_id"] = "ORPHAN"
    plant(c, line["invoice_id"], line["line_no"], "orphan_supplier",
          "Supplier 'Mystery Traders Pty Ltd' not in reference data")

    # 7. Unknown category: sale with no tax code (and sales have no supplier default)
    line = find(lines, txn_type="sale", line_no=1)
    line["tax_code"] = ""
    plant(c, line["invoice_id"], line["line_no"], "unknown_category",
          "No tax code and no supplier default")

    # 8. Blank destination on a sale
    line = [l for l in lines if l["txn_type"] == "sale" and l["tax_code"]][3]
    line["destination"] = ""
    plant(c, line["invoice_id"], line["line_no"], "missing_destination", "Sale with no destination")

    # 9. Duplicate line: exact copy of an existing line
    dup = dict(find(lines, supplier_id="S04"))
    lines.append(dup)
    plant(c, dup["invoice_id"], dup["line_no"], "duplicate_line", "Same invoice and line twice")

    # 10. Invalid country: written in full instead of an ISO code. Must NOT become an export
    line = [l for l in lines if l["txn_type"] == "sale" and l["tax_code"] and l["destination"] == "AU"][6]
    line["destination"] = "Australia"
    plant(c, line["invoice_id"], line["line_no"], "invalid_country",
          "'Australia' isn't an ISO code. Skip the export rule and flag")

    # 11. Purchase with no supplier at all
    line = [l for l in lines if l["supplier_id"] == "S07"][2]
    line["supplier_id"] = ""
    plant(c, line["invoice_id"], line["line_no"], "missing_supplier", "Purchase with a blank supplier")

    # 12. Re-submitted invoice: whole invoice copied under a new number
    original_id = find(lines, supplier_id="S03")["invoice_id"]
    for l in [l for l in lines if l["invoice_id"] == original_id]:
        copy = dict(l, invoice_id="A-INV-9001")
        lines.append(copy)
    plant(c, "A-INV-9001", None, "possible_resubmitted_invoice",
          f"Copy of {original_id}: same supplier, date and total, new number")


def plant_client_b(lines):
    c = "client_b"

    # 1. Outlier: huge software purchase
    line = find(lines, supplier_id="S06")
    line["net"] = Decimal("22727.27")
    line["gst"] = money(line["net"] * Decimal("0.10"))
    plant(c, line["invoice_id"], line["line_no"], "amount_outlier", "Unusually large software purchase")

    # 2. Rounding edge case: 3 lines of $10.05 incl GST, client uses the total invoice rule.
    #     Line GST shows 0.92, 0.91, 0.91 (= 2.74). Engine (taxable sale rule) expects 0.91 each.
    #     Each line is within the 1 cent tolerance, so this must NOT be flagged.
    for n, gst in enumerate(["0.92", "0.91", "0.91"], start=1):
        lines.append({"invoice_id": "B-INV-9001", "line_no": n, "date": pd.Timestamp("2026-08-14"),
                      "doc_type": "invoice", "txn_type": "purchase", "supplier_id": "S05",
                      "tax_code": "ST", "description": "Whiteboard markers",
                      "net": Decimal("10.05") - Decimal(gst), "gst": Decimal(gst), "destination": "AU"})
    plant(c, "B-INV-9001", None, "none",
          "Total invoice rule rounding (2.74 vs 2.73). Within tolerance, should not be flagged")

    # 3. Category conflict: single-category supplier (software) line coded as basic food
    line = [l for l in lines if l["supplier_id"] == "S06"][1]  # not the outlier line
    line["tax_code"] = "BF"
    line["gst"] = Decimal("0.00")
    plant(c, line["invoice_id"], line["line_no"], "category_conflict",
          "Software supplier line coded as basic food")

    # 4. Tax code that isn't in tax_codes.csv
    line = [l for l in lines if l["supplier_id"] == "S04"][3]
    line["tax_code"] = "ZZ"
    plant(c, line["invoice_id"], line["line_no"], "unmapped_tax_code",
          "Code 'ZZ' isn't in tax_codes.csv. Fall back to supplier default and flag")

    # 5. Invalid date (31 Feb) and 6. missing amount: handled when writing the file below


# ---------------------------------------------------------------------------
# Writers: each client exports in its own format
# ---------------------------------------------------------------------------
def write_client_a(lines):
    """Client A: GST-exclusive amounts, ISO dates, short codes."""
    name = lambda sid: "Mystery Traders Pty Ltd" if sid == "ORPHAN" else NAME_FOR.get(sid, "")
    df = pd.DataFrame([{
        "InvoiceNo": l["invoice_id"], "LineNo": l["line_no"],
        "DocType": "CRN" if l["doc_type"] == "credit_note" else "INV",
        "TxnType": "S" if l["txn_type"] == "sale" else "P",
        "Vendor": name(l["supplier_id"]), "TaxCd": l["tax_code"], "Desc": l["description"],
        "NetAmt": l["net"], "GSTAmt": l["gst"],
        "InvDate": l["date"].strftime("%Y-%m-%d"), "ShipTo": l["destination"],
    } for l in lines])
    df.to_csv(RAW / "client_a.csv", index=False)
    return df


def write_client_b(lines):
    """Client B: GST-inclusive totals, DD/MM/YYYY dates, lowercase names."""
    df = pd.DataFrame([{
        "inv_id": l["invoice_id"], "line": l["line_no"],
        "doc": "credit" if l["doc_type"] == "credit_note" else "invoice",
        "type": l["txn_type"], "supplier_name": NAME_FOR.get(l["supplier_id"], ""),
        "code": l["tax_code"], "item": l["description"],
        "total_inc_gst": l["net"] + l["gst"], "gst": l["gst"],
        "date": l["date"].strftime("%d/%m/%Y"), "country": l["destination"],
    } for l in lines])

    # 5. Invalid date
    i = 5
    df.loc[i, "date"] = "31/02/2026"
    plant("client_b", df.loc[i, "inv_id"], int(df.loc[i, "line"]), "invalid_date", "31 February doesn't exist")

    # 6. Missing required amount
    i = 12
    df.loc[i, "total_inc_gst"] = None
    plant("client_b", df.loc[i, "inv_id"], int(df.loc[i, "line"]), "missing_required_field",
          "Amount is blank")

    df.to_csv(RAW / "client_b.csv", index=False)
    return df


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)

    SUPPLIERS.to_csv(REF / "suppliers.csv", index=False)
    TAX_CODES.to_csv(REF / "tax_codes.csv", index=False)

    a = make_lines("client_a", 60)
    plant_client_a(a)
    df_a = write_client_a(a)

    b = make_lines("client_b", 60)
    plant_client_b(b)
    df_b = write_client_b(b)

    planted_df = pd.DataFrame(planted)
    planted_df["line_no"] = planted_df["line_no"].astype("Int64")  # whole numbers, blank if whole invoice
    planted_df.to_csv(REF / "planted_errors.csv", index=False)
    print(f"client_a.csv: {len(df_a)} lines | client_b.csv: {len(df_b)} lines | "
          f"planted problems: {len(planted)}")


if __name__ == "__main__":
    main()
