# GST Rules Engine & Data Quality Pipeline

![tests](https://github.com/rojajoshi/gst-rules-engine/actions/workflows/ci.yml/badge.svg)

Tax teams receive transaction data from many clients, and every client's file looks different: different column names, date formats and codes. Before GST can be worked out, that data has to be standardised and checked, because one bad row can make a BAS wrong.

This project is a small pipeline that does that for simplified Australian GST. It maps messy client files into one standard format, checks them for data quality problems, then applies GST rules, with every result traceable back to the source row and the rule that produced it.

**Status: in progress...**

## What's done

- **Rules specification** ([docs/rules_spec.md](docs/rules_spec.md)): GST treatment rules in priority order (taxable, GST-free, input-taxed), rounding, credit notes and BAS labels, based on ATO guidance, with worked examples and a log of open questions
- **Standard schema** ([config/schema.yaml](config/schema.yaml), [docs/data_dictionary.md](docs/data_dictionary.md)): every column, type and quality check in one place
- **Synthetic data** ([scripts/generate_data.py](scripts/generate_data.py)): two fictional clients with different file layouts and 19 deliberately planted errors (impossible dates, unknown suppliers, GST mismatches, duplicates, outliers), listed in `planted_errors.csv`
- **Config-driven ingest** ([src/gst_engine/ingest.py](src/gst_engine/ingest.py)): onboarding a new client means writing a small YAML mapping, not changing code. Money is handled as exact decimals, and original values and source row numbers are kept for traceability
- **Automated tests** with pytest, running on every push via GitHub Actions

## What's next

- Data quality checks, including median-based (MAD) outlier detection
- The rules engine: GST treatment, expected GST and the rule that fired, for every row
- Reconciliation: proving the pipeline catches all 19 planted errors
- A BAS summary in SQL (DuckDB)

## Run it

    pip install -r requirements.txt
    python scripts/generate_data.py
    pytest -v

## Notes

All data is synthetic and all supplier names are fictional. The GST rules are deliberately simplified for learning purposes and are not tax advice.
