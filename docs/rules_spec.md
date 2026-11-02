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

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R01-1 | sale | software | NZ | 1000.00 | GST-free | 0.00 | N/A | R01: Overseas destination; export rule applies. |
| R01-2 | sale | stationery | JP | 200.00 | GST-free | 0.00 | N/A | R01: Export rule overrides the normally taxable category. |
| R01-3 | sale | stationery | blank | 100.00 | Taxable | 10.00 | N/A | R01 skipped because destination is blank; default taxable rule applies. |
| R01-4 | sale | stationery | AU | 100.00 | Taxable | 10.00 | N/A | R01 skipped because the sale is domestic; default taxable rule applies. |
| R01-5 | sale | basic_food | blank | 100.00 | GST-free | 0.00 | N/A | R01 skipped because destination is blank; basic food category rule applies. |

### R02: Financial supplies

- Applies to: Sales or purchases categorised as `financial_services`.
- Treatment: Input-taxed (0% GST). No GST is charged on sales. GST credits generally cannot be claimed on purchases relating to making input-taxed financial supplies.
- Priority: 2, checked after R01.
- Exceptions:
  - Not everything supplied by a financial institution is a financial supply.
  - Providing a credit card facility is an input-taxed financial supply.
  - Providing interchange services is a taxable supply. These must use a different category, such as `payment_processing`, to distinguish them from financial supplies.
- Engine logic:
  - If `category` = `financial_services` (sale or purchase), classify as input-taxed.
  - Set `expected_gst` = `0.00`.
  - If `transaction_type` = `purchase`, set `credit_claimable` = `No`.
  - If `transaction_type` = `sale`, set `credit_claimable` = `N/A`.
  - Check R02 only if R01 has not already matched.
  - If `category` = `payment_processing`, skip R02 and continue to the relevant category-based rule.
- Assumptions (not modelled):
  - Assume an overseas financial supply is GST-free under R01 when both R01 and R02 could apply. R01 takes precedence until confirmed by a tax SME.
  - Assume clients do not make input-taxed financial supplies when calculating GST credits on their other taxable purchases.
  - GST credit apportionment for businesses making both taxable and input-taxed supplies is not modelled.
  - Reduced input tax credits are not modelled.
  - Assume `financial_services` is assigned only to transactions that qualify as financial supplies.
  - Interchange services are assigned to `payment_processing`, rather than `financial_services`.
- Source:
  - ATO, [Input-taxed sales](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/when-to-charge-gst-and-when-not-to/input-taxed-sales).
  - ATO, [Financial supplies](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/when-to-charge-gst-and-when-not-to/input-taxed-sales/financial-supplies).

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R02-1 | purchase | financial_services | AU | 500.00 | Input-taxed | 0.00 | No | R02: Loan interest; no GST is included in the price. |
| R02-2 | purchase | financial_services | AU | 20.00 | Input-taxed | 0.00 | No | R02: Assumed input-taxed bank account fee. |
| R02-3 | sale | financial_services | AU | 1000.00 | Input-taxed | 0.00 | N/A | R02: Interest earned from a qualifying lending arrangement. |
| R02-4 | sale | financial_services | AU | 100.00 | Input-taxed | 0.00 | N/A | R02: Providing a credit card facility. |
| R02-5 | sale | financial_services | US | 1000.00 | GST-free | 0.00 | N/A | R01: Overseas destination; R01 takes precedence under the current assumption. |
| R02-6 | sale | payment_processing | AU | 100.00 | Taxable | 10.00 | N/A | R02 is skipped because the category is different; interchange services use `payment_processing`, so the transaction falls to the default taxable rule. |

### R03: Taxable food

- **Applies to:** Transactions categorised as `taxable_food`.
- **Treatment:** Taxable (10% GST).
- **Priority:** 3, checked after R01 and R02. R03 is placed before R04 so taxable food is checked before basic food.
- **Exceptions:**
  - Not all cooked food is taxable. For example, cold cooked chicken is GST-free.
  - Freshly baked bread that is still warm is generally GST-free, unless it falls into another taxable food category.
  - Hampers containing separate taxable and GST-free products are treated as mixed supplies, rather than being classified entirely as taxable food.
- **Engine logic:**
  - Check R03 only if R01 and R02 have not already matched.
  - If `category` = `taxable_food`, classify as taxable for both sales and purchases.
  - Calculate `expected_gst` as `net_amount` × 0.10, assuming the amount is GST-exclusive.
  - If `transaction_type` = `purchase`, set `credit_claimable` = `Yes`, assuming a registered supplier and a creditable business purchase. Otherwise, set it to `N/A`.
  - If the category does not match, continue to R04 or the default rule.
- **Assumptions (not modelled):**
  - Assume food categories have been assigned correctly upstream using ATO guidance and supplier information.
  - Assume taxable food products, including prepared meals, confectionery, savoury snacks and soft drinks, are assigned to `taxable_food`.
  - Detailed product classification and mixed-supply handling are resolved during category assignment, not by the GST engine.
- **Sources:**
  - ATO, [Taxable food](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/taxable-food).
  - ATO, [Detailed Food List](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/detailed-food-list).

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R03-1 | sale | taxable_food | AU | 20.00 | Taxable | 2.00 | N/A | R03: Hot takeaway chicken is taxable. |
| R03-2 | sale | taxable_food | AU | 25.00 | Taxable | 2.50 | N/A | R03: Restaurant meal supplied for consumption on the premises. |
| R03-3 | purchase | taxable_food | AU | 12.00 | Taxable | 1.20 | Yes | R03: Chocolate is taxable and GST credits can generally be claimed on a qualifying business purchase. |

### R04: Basic food

- **Applies to:** Transactions categorised as `basic_food` that qualify as GST-free food.
- **Treatment:** GST-free (0% GST).
- **Priority:** 4, checked after R01, R02 and R03. R03 is placed first so taxable food categories are checked before basic food. If every item has one correct category, the order between R03 and R04 does not change the outcome.
- **Exceptions:**
  - Not all food is GST-free. Some prepared foods, confectionery, savoury snacks and drinks are taxable.
  - Hot takeaway chicken is taxable, while cold cooked chicken is GST-free.
  - Food supplied for consumption on the premises is taxable.
- **Engine logic:**
  - Check R04 only if R01, R02 and R03 have not already matched.
  - If `category` = `basic_food`, classify as GST-free for both sales and purchases.
  - Set `expected_gst` = `0.00`.
  - If `transaction_type` = `purchase`, set `credit_claimable` = `No`, because no GST was charged. Otherwise, set it to `N/A`.
  - If the category does not match, continue to the default taxable rule.
- **Assumptions (not modelled):**
  - Assume food categories have been assigned correctly upstream using ATO guidance and supplier information.
  - Assume ordinary food staples, such as fresh fruit, vegetables, raw meat, milk and plain bread, are categorised as `basic_food`.
  - Assume the distinction between taxable and GST-free food is resolved during category assignment, rather than by the GST engine.
- **Sources:**
  - ATO, [GST-free food](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/gst-free-food).
  - ATO, [Detailed Food List](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/detailed-food-list).

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R04-1 | sale | basic_food | AU | 10.00 | GST-free | 0.00 | N/A | R04: Fresh fruit is basic food. |
| R04-2 | sale | basic_food | AU | 15.00 | GST-free | 0.00 | N/A | R04: Cold cooked chicken is GST-free. |
| R04-3 | purchase | basic_food | AU | 8.00 | GST-free | 0.00 | No | R04: Plain bread is GST-free, so there is no GST credit to claim. |


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
|---|---|---|
| Is hot roast chicken GST-free? | No. Hot takeaway chicken is taxable and should be categorised as `taxable_food`. | ATO Detailed Food List |
| Is cold cooked chicken GST-free? | Yes. Cold cooked chicken is generally GST-free and should be categorised as `basic_food`. | ATO Detailed Food List |
| Is warm fresh bread taxable? | No. Bread that is still warm because it has just been baked is generally GST-free, unless it falls into another taxable food category. | ATO, GST and food |
| Are hampers containing taxable and GST-free products entirely taxable? | No. A hamper containing separate, individually packaged products is generally a mixed supply. The taxable and GST-free components are treated separately, with the value apportioned where needed. | ATO, Mixed GST status on food products |
| Are snacks, confectionery and soft drinks GST-free? | Many are taxable. Examples include chocolate, lollies, potato crisps and soft drinks. These should be categorised as `taxable_food`. | ATO Detailed Food List |

## Open questions for a tax SME
### Open Questions

| Question | Related rule | Current assumption | Impact if assumption is wrong |
|---|---|---|---|
| Should overseas financial supplies be GST-free under R01 or input-taxed under R02? | R01 / R02 | R01 takes priority when both rules match. | Incorrect GST classification for overseas financial supplies, potentially resulting in incorrect BAS reporting. |
| How should GST credits be apportioned for clients making both taxable and input-taxed sales? | R02 | Assume clients do not make input-taxed sales affecting their GST credit entitlement. | The engine may overstate GST credits on taxable purchases relating to input-taxed supplies. |

