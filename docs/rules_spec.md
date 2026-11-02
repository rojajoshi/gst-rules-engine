# GST Rules Specification

## Scope and assumptions
(What this covers, what it doesn't, "simplified, not tax advice", BAS method chosen)

## Treatment rules
### R01: Exports

- Applies to: Sales of goods and services with a destination outside Australia.
- Treatment: GST-free (0% GST). GST credits can still be claimed on related purchases.
- Priority: Priority 1. Exports must be checked before category-based rules because an otherwise taxable category can qualify as GST-free when exported.
- Exceptions:
  - Services provided to customers in Australia may be taxable, even if an overseas party pays.
  - Unknown customer locations cannot be confirmed as GST-free.
- Engine logic:
    - If `transaction_type` = `sale` and `destination_country` is not blank and not `AU`, classify as GST-free.
    - If `destination_country` is blank, skip the export rule and flag a data quality issue, then continue to category-based rules.
    - If `destination_country` = `AU`, skip the export rule and continue to category-based rules.
    - Exports apply to sales, not purchases.
- Assumptions (not modelled):
  - Assume goods are exported within 60 days of the earlier of first payment or invoice (12 months for new recreational boats).
  - Assume the supplier exports the goods.
  - Assume `destination_country` reflects where a service is used or enjoyed.
- Source: ATO, Exports and GST; GSTR 2002/6; s38-185 GST Act.

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | Why |
|---|---|---|---|---:|---|---:|---|
| R01-1 | sale | software | NZ | 1000.00 | GST-free | 0.00 | Overseas destination |
| R01-2 | sale | stationery | JP | 200.00 | GST-free | 0.00 | Export overrides normally taxable category |
| R01-3 | sale | stationery | blank | 100.00 | Taxable | 10.00 | Blank destination skips the export rule; stationery is taxable by default |
| R01-4 | sale | stationery | AU | 100.00 | Taxable | 10.00 | Domestic sale; export rule does not apply |
| R01-5 | sale | basic_food | blank | 100.00 | GST-free | 0.00 | Blank destination skips the export rule; the basic food category rule determines the treatment |

## Calculation rules
### GST-exclusive amounts
### GST-inclusive amounts
### Non-taxable lines
### Rounding

## Category resolution
(tax code → supplier default → unknown)

## GST credits on purchases

## BAS summary rules
### G1 / 1A / 1B

## Resolved questions
| Question | Answer | Source |

## Open questions for a tax SME
| Question | Assumption | Impact if wrong |