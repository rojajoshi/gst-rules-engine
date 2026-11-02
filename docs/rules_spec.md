# GST Rules Specification

## Scope and assumptions
(What this covers, what it doesn't, "simplified, not tax advice", BAS method chosen)

## Treatment rules

### R01: Exports

- **Applies to:** Sales of goods and services with a destination outside Australia.
- **Treatment:** GST-free (0% GST). GST credits can still be claimed on related purchases.
- **Priority:** 1. Exports must be checked before category-based rules because an otherwise taxable category can qualify as GST-free when exported.
- **Exceptions:**
  - Services provided to customers in Australia may be taxable, even if an overseas party pays.
  - Unknown customer locations cannot be confirmed as GST-free.
- **Engine logic:**
  - If `transaction_type` = `sale` and `destination_country` is not blank and not `AU`, classify as GST-free.
  - If `destination_country` is blank, skip the export rule and flag a data quality issue, then continue to category-based rules.
  - If `destination_country` = `AU`, skip the export rule and continue to category-based rules.
  - Exports apply to sales, not purchases.
- **Assumptions (not modelled):**
  - Assume goods are exported within 60 days of the earlier of first payment or invoice (12 months for new recreational boats).
  - Assume the supplier exports the goods.
  - Assume `destination_country` reflects where a service is used or enjoyed.
- **Sources:**
  - ATO, [Exports and GST](https://www.ato.gov.au/businesses-and-organisations/international-tax-for-business/australians-doing-business-overseas/exports-and-gst).
  - GSTR 2002/6; s38-185 GST Act.

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R01-1 | sale | software | NZ | 1000.00 | GST-free | 0.00 | N/A | R01: Overseas destination; export rule applies. |
| R01-2 | sale | stationery | JP | 200.00 | GST-free | 0.00 | N/A | R01: Export rule overrides the normally taxable category. |
| R01-3 | sale | stationery | blank | 100.00 | Taxable | 10.00 | N/A | R01 skipped because destination is blank; R99 default taxable rule applies. |
| R01-4 | sale | stationery | AU | 100.00 | Taxable | 10.00 | N/A | R01 skipped because the sale is domestic; R99 default taxable rule applies. |
| R01-5 | sale | basic_food | blank | 100.00 | GST-free | 0.00 | N/A | R01 skipped because destination is blank; R04 basic food rule applies. |

### R02: Financial supplies

- **Applies to:** Sales or purchases categorised as `financial_services`.
- **Treatment:** Input-taxed (0% GST). No GST is charged on sales. GST credits generally cannot be claimed on purchases relating to making input-taxed financial supplies.
- **Priority:** 2, checked after R01. Exports are checked first, so an overseas financial supply is treated as GST-free (see Open questions).
- **Exceptions:**
  - Not everything supplied by a financial institution is a financial supply.
  - Providing a credit card facility is an input-taxed financial supply.
  - Providing interchange services is a taxable supply. These must use a different category, such as `payment_processing`, to distinguish them from financial supplies.
- **Engine logic:**
  - Check R02 only if R01 has not already matched.
  - If `category` = `financial_services` (sale or purchase), classify as input-taxed.
  - Set `expected_gst` = `0.00`.
  - If `transaction_type` = `purchase`, set `credit_claimable` = `No`.
  - If `transaction_type` = `sale`, set `credit_claimable` = `N/A`.
  - If `category` = `payment_processing`, skip R02 and continue to the remaining rules.
- **Assumptions (not modelled):**
  - Assume an overseas financial supply is GST-free under R01 when both R01 and R02 could apply. R01 takes precedence until confirmed by a tax SME.
  - Assume clients do not make input-taxed financial supplies when calculating GST credits on their other taxable purchases.
  - GST credit apportionment for businesses making both taxable and input-taxed supplies is not modelled.
  - Reduced input tax credits are not modelled.
  - Assume `financial_services` is assigned only to transactions that qualify as financial supplies.
  - Interchange services are assigned to `payment_processing`, rather than `financial_services`.
- **Sources:**
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
| R02-6 | sale | payment_processing | AU | 100.00 | Taxable | 10.00 | N/A | R02 skipped because interchange services use `payment_processing`; R99 default taxable rule applies. |

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
  - If the category does not match, continue to the remaining rules.
- **Assumptions (not modelled):**
  - Assume food categories have been assigned correctly upstream using ATO guidance and supplier information.
  - Assume taxable food products, including prepared meals, confectionery, savoury snacks and soft drinks, are assigned to `taxable_food`.
  - Detailed product classification and mixed-supply handling are resolved during category assignment, not by the GST engine.
- **Sources:**
  - ATO, [Taxable food](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/taxable-food).
  - ATO, [Detailed food list](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/detailed-food-list).

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R03-1 | sale | taxable_food | AU | 20.00 | Taxable | 2.00 | N/A | R03: Hot takeaway chicken is taxable. |
| R03-2 | sale | taxable_food | AU | 25.00 | Taxable | 2.50 | N/A | R03: Restaurant meal supplied for consumption on the premises. |
| R03-3 | purchase | taxable_food | AU | 12.00 | Taxable | 1.20 | Yes | R03: Chocolate is taxable, and GST credits can generally be claimed on a qualifying business purchase. |

### R04: Basic food

- **Applies to:** Transactions categorised as `basic_food`.
- **Treatment:** GST-free (0% GST).
- **Priority:** 4, checked after R01, R02 and R03. If every item has one correct category, the order between R03 and R04 does not change the outcome. R03 is placed first so taxable food exceptions stay visible.
- **Exceptions:**
  - Not all food is GST-free. Some prepared foods, confectionery, savoury snacks and drinks are taxable.
  - Hot takeaway chicken is taxable, while cold cooked chicken is GST-free.
  - Food supplied for consumption on the premises is taxable.
- **Engine logic:**
  - Check R04 only if R01, R02 and R03 have not already matched.
  - If `category` = `basic_food`, classify as GST-free for both sales and purchases.
  - Set `expected_gst` = `0.00`.
  - If `transaction_type` = `purchase`, set `credit_claimable` = `No`, because no GST was charged. Otherwise, set it to `N/A`.
  - If the category does not match, continue to the remaining rules.
- **Assumptions (not modelled):**
  - Assume food categories have been assigned correctly upstream using ATO guidance and supplier information.
  - Assume ordinary food staples, such as fresh fruit, vegetables, raw meat, milk and plain bread, are categorised as `basic_food`.
  - Assume the distinction between taxable and GST-free food is resolved during category assignment, rather than by the GST engine.
- **Sources:**
  - ATO, [GST-free food](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/gst-free-food).
  - ATO, [Detailed food list](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/detailed-food-list).

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R04-1 | sale | basic_food | AU | 10.00 | GST-free | 0.00 | N/A | R04: Fresh fruit is basic food. |
| R04-2 | sale | basic_food | AU | 15.00 | GST-free | 0.00 | N/A | R04: Cold cooked chicken is GST-free. |
| R04-3 | purchase | basic_food | AU | 8.00 | GST-free | 0.00 | No | R04: Plain bread is GST-free, so there is no GST credit to claim. |

### R05: Medical and other health services

- **Applies to:** Transactions categorised as `gst_free_medical` or `gst_free_other_health`.
- **Treatment:** GST-free (0% GST).
- **Priority:** 5, checked after R01 to R04. Categories don't overlap, so the order among category rules doesn't change the outcome.
- **Exceptions:**
  - Cosmetic procedures are generally taxable where no Medicare benefit is payable and the procedure is performed for cosmetic reasons.
  - Other health services must be on the ATO's listed services and provided by a recognised professional.
  - Medical reports and health-related products are not automatically GST-free.
- **Engine logic:**
  - Check R05 only if R01 to R04 have not already matched.
  - If `category` = `gst_free_medical` or `gst_free_other_health`, classify as GST-free for both sales and purchases.
  - Set `expected_gst` = `0.00`.
  - If `transaction_type` = `purchase`, set `credit_claimable` = `No`. Otherwise, set it to `N/A`.
  - If the category does not match, continue to the R99 default taxable rule.
- **Assumptions (not modelled):**
  - Assume medical and health service categories have been assigned correctly upstream using ATO guidance and supplier information.
  - Assume Medicare eligibility, provider recognition and appropriate treatment requirements have been checked during category assignment.
  - Assume cosmetic procedures and non-qualifying health services are not assigned to either GST-free category.
  - Assume separately sold health products are handled under the relevant goods classification rules.
- **Sources:**
  - ATO, [Medical services](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-health/medical-services).
  - ATO, [Other health services](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-health/other-health-services).

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R05-1 | sale | gst_free_medical | AU | 100.00 | GST-free | 0.00 | N/A | R05: Medical consultation for which a Medicare benefit is payable. |
| R05-2 | sale | gst_free_other_health | AU | 80.00 | GST-free | 0.00 | N/A | R05: Physiotherapy supplied by a recognised professional as appropriate treatment. |
| R05-3 | purchase | gst_free_medical | AU | 100.00 | GST-free | 0.00 | No | R05: Medical service is GST-free, so there is no GST credit to claim. |
| R05-4 | sale | cosmetic_procedure | AU | 500.00 | Taxable | 50.00 | N/A | R05 skipped because cosmetic procedures aren't assigned a GST-free health category; R99 default taxable rule applies. |

### R99: Default taxable

- **Applies to:** Sales and purchases that have not matched any preceding GST treatment rule.

- **Treatment:** Taxable (10% GST), assuming the amount is GST-exclusive.

- **Priority:** 99, checked last after R01 to R05. R99 is the fallback rule when no specific rule matches.

- **Exceptions:**
  - GST-free and input-taxed transactions must be classified by their specific rules before R99 applies.
  - Transactions with an `unknown` category receive the default taxable treatment but are flagged for review by the quality checks.

- **Engine logic:**
  - Check R99 only if R01 to R05 have not already matched.
  - Classify the transaction as taxable.
  - Calculate `expected_gst` as `net_amount` × 0.10.
  - If `transaction_type` = `purchase` and `category` = `unknown`, set `credit_claimable` = `Review`.
  - If `transaction_type` = `purchase` and `category` is known, set `credit_claimable` = `Yes`. If `transaction_type` = `sale`, set `credit_claimable` = `N/A`.
  - Unknown categories and missing destination information are flagged separately by the quality checks.

- **Assumptions (not modelled):**
  - Assume all transactions are made by a GST-registered client in the course of their business and meet the other requirements for taxable treatment unless a specific rule applies.
  - Assume `net_amount` is GST-exclusive.
  - Detailed GST credit eligibility, including supplier registration and creditable acquisition requirements, is handled separately in the GST credits section.

- **Sources:**
  - ATO, [GST-free sales](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/when-to-charge-gst-and-when-not-to/gst-free-sales).
  - ATO, [Input-taxed sales](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/when-to-charge-gst-and-when-not-to/input-taxed-sales).
  - A New Tax System (Goods and Services Tax) Act 1999, section 9-5.

#### Examples

| Case | transaction_type | category | destination_country | net_amount | Expected treatment | Expected GST | credit_claimable | Why |
|---|---|---|---|---:|---|---:|---|---|
| R99-1 | sale | stationery | AU | 100.00 | Taxable | 10.00 | N/A | R99: No preceding rule matches; default taxable treatment applies. |
| R99-2 | sale | cosmetic_procedure | AU | 500.00 | Taxable | 50.00 | N/A | R99: No GST-free health rule matches; default taxable treatment applies. |
| R99-3 | sale | unknown | AU | 100.00 | Taxable | 10.00 | N/A | R99: Default taxable treatment applies; unknown category is flagged by quality checks. |
| R99-4 | purchase | unknown | AU | 100.00 | Taxable | 10.00 | Review | R99: Default taxable treatment applies; credit eligibility requires review. |
| R99-5 | purchase | stationery | AU | 100.00 | Taxable | 10.00 | Yes | R99: Known taxable category; credit claimable, assuming a registered supplier. |

## Calculation rules

### GST-exclusive amounts

- **Formula:** `expected_gst` = `net_amount` × 0.10.
- **Explanation:** When an amount is GST-exclusive, GST is calculated as 10% of the amount.
- **Source:** ATO, [Tax invoices](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/tax-invoices).

**Example:**

| net_amount | amount_type | Expected GST | Expected total |
|---:|---|---:|---:|
| 100.00 | GST-exclusive | 10.00 | 110.00 |

### GST-inclusive amounts

- **Formula:** `expected_gst` = `gross_amount` ÷ 11.
- **Explanation:** A GST-inclusive price contains 110% of the original price: 100% net amount plus 10% GST. Therefore, GST represents 10/110, which simplifies to 1/11 of the total price.
- **Source:** ATO, [Tax invoices](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/tax-invoices).

**Example:**

| gross_amount | amount_type | Expected GST | Expected net amount |
|---:|---|---:|---:|
| 110.00 | GST-inclusive | 10.00 | 100.00 |

### Non-taxable lines

- **Formula:** `expected_gst` = `0.00`, regardless of whether the amount is GST-inclusive or GST-exclusive.
- **Explanation:** GST-free and input-taxed supplies do not have GST added to their price. For a GST-inclusive non-taxable amount, the entire amount remains the net amount for this calculation.
- **Source:** ATO, [GST-free sales](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/when-to-charge-gst-and-when-not-to/gst-free-sales) and [Input-taxed sales](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/when-to-charge-gst-and-when-not-to/input-taxed-sales).

**Example:**

| Description | gross_amount | Expected treatment | Expected GST | Expected net amount |
|---|---:|---|---:|---:|
| Basic food | 110.00 | GST-free | 0.00 | 110.00 |

### Rounding

Two ATO-approved approaches can be used to calculate GST across multiple taxable sale lines:

- **Taxable sale rule:** Calculate GST separately for each line, round each result to two decimal places, then add the rounded amounts to get the invoice GST total.
- **Total invoice rule:** Calculate GST separately for each line without rounding, add the unrounded amounts together, then round the final invoice GST total to two decimal places.

**Engine decision:**

Use the **taxable sale rule (round each line, then sum)**.

This approach is straightforward to implement because each transaction line can be calculated and rounded independently. It also aligns with displaying GST amounts per line on an invoice, making individual line calculations easier to check and reconcile.

- **Source:** ATO, [Tax invoices](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/tax-invoices) ("Rounding of GST" section). The ATO also states that suppliers and customers don't need to use the same rounding rule.

**Example 1: Three GST-inclusive lines of $10.05**

Each line has an exact GST amount of `10.05 / 11 = 0.913636...`

| Calculation | Taxable sale rule | Total invoice rule |
|---|---:|---:|
| Line 1 | 0.91 | 0.913636... |
| Line 2 | 0.91 | 0.913636... |
| Line 3 | 0.91 | 0.913636... |
| Total before final rounding | 2.73 | 2.740909... |
| **Final invoice GST** | **2.73** | **2.74** |

Difference: $0.01.

**Example 2: Ten GST-inclusive lines of $10.04**

Each line has an exact GST amount of `10.04 / 11 = 0.912727...`

| Calculation | Taxable sale rule | Total invoice rule |
|---|---:|---:|
| Each line | 0.91 | 0.912727... |
| Total before final rounding | 9.10 | 9.127272... |
| **Final invoice GST** | **9.10** | **9.13** |

Difference: $0.03. The gap grows with the number of lines, because each line's rounding can shift by up to half a cent in the same direction.

**Rounding tolerance:**

- **Line level:** allow a maximum difference of $0.01 per line.
- **Invoice level:** allow a maximum difference of $0.01 × the number of taxable lines on the invoice.
- These tolerances exist because a client may legitimately use the other ATO-approved rounding rule, which can produce small differences that grow with invoice length.
- The tolerance only covers rounding differences, not larger calculation errors. Any difference above it is flagged.

**Rounding convention:**

- Round half up: amounts of exactly half a cent or more round up to the next cent.
- For example, `$1.235` becomes `$1.24`.
- Use Python's `Decimal` with `ROUND_HALF_UP` for GST calculations. Do not use Python's default `round()`, which uses round half to even.

## Category resolution

Category resolution determines which category is assigned to each transaction line before the GST treatment rules are applied.

### Assumptions

- Each tax code in `tax_codes.csv` maps to a single category.
- Each supplier in `suppliers.csv` has a default category, where available.
- Each supplier has a `multi_category` field indicating whether it regularly supplies goods or services across multiple categories.

**Note:** This assumes client-specific tax code mappings are available. Real ERP tax codes may represent GST treatment rather than a specific category. For example, a `GST` or `FRE` tax code alone may not distinguish basic food from other goods. This assumption is listed in the Open questions.

### Resolution order

Use the following priority order:

1. **Tax code:** If a tax code is available for the transaction line, use the category mapped to that tax code.
2. **Supplier default:** If no tax code is available, use the supplier's default category, if one exists.
3. **Unknown:** If neither a tax code nor a supplier default is available, assign `unknown`.

### Why the tax code takes priority

The tax code is assigned at the transaction-line level, so it can reflect the specific item or service being purchased or sold.

A supplier default applies to the supplier as a whole and may not accurately represent every transaction.

For example, a supermarket sells both basic food and taxable goods. Its supplier default might be `basic_food`, but this would incorrectly classify items such as cleaning products or cooked food. A tax code assigned to each line can distinguish between these categories.

Therefore, the tax code takes priority over the supplier default.

### Category source

Record how each category was determined using the `category_source` field.

| Value | Meaning |
|---|---|
| `tax_code` | Category determined from the transaction-line tax code |
| `supplier_default` | Category determined from the supplier's default because no tax code was available |
| `unknown` | Neither a tax code nor a supplier default was available |

### Handling unknown categories

If neither a tax code nor a supplier default is available:

- Set `category` to `unknown`.
- Set `category_source` to `unknown`.
- Allow R99 to apply the default taxable treatment.
- Flag the transaction through the quality checks for review.

The quality flag does not change the provisional treatment assigned by R99.

### Conflicting tax codes and supplier defaults

If the tax code and supplier default indicate different categories, the tax code takes priority because it is specific to the transaction line.

However, the disagreement is checked against the supplier's `multi_category` setting:

- If `multi_category` = `true`, the disagreement is expected and does not generate a quality flag.
- If `multi_category` = `false`, flag the disagreement for review, because the supplier is expected to operate within a single category.

For example, a supermarket has a supplier default of `basic_food`, but a transaction line has tax code `TF` (mapped to `taxable_food`):

- Resolve the category as `taxable_food`.
- Set `category_source` to `tax_code`.
- Do not flag the disagreement, because the supermarket has `multi_category` = `true`.
- Apply the GST treatment rules for `taxable_food`.

For a single-category supplier, the disagreement is flagged, but the tax code still takes priority. The flag does not override the resolved category.

### Examples

Tax codes used below (final list defined in `tax_codes.csv`):
`TF` = `taxable_food`, `BF` = `basic_food`.

| Case | tax_code | supplier_default | multi_category | Resolved category | category_source | Flag? |
|---|---|---|---|---|---|---|
| CR-1 | `TF` | `basic_food` | true | `taxable_food` | `tax_code` | No: expected for a multi-category supplier |
| CR-2 | blank | `stationery` | false | `stationery` | `supplier_default` | No |
| CR-3 | blank | blank | N/A | `unknown` | `unknown` | Yes: unknown category |
| CR-4 | `BF` | `stationery` | false | `basic_food` | `tax_code` | Yes: unexpected disagreement for a single-category supplier |

### Supplier configuration

Add the following field to `suppliers.csv`:

| Field | Type | Meaning |
|---|---|---|
| `multi_category` | Boolean | Whether the supplier regularly supplies goods or services across multiple categories. |

This field is used by quality checks to distinguish expected category differences from potentially incorrect supplier or tax code mappings.

## GST credits on purchases

The `credit_claimable` field determines whether a purchase is eligible for a GST credit. Credit eligibility is determined separately from category resolution and GST treatment because it depends on both what was purchased and whether the supplier was registered for GST.

- **Source:** ATO, [Simpler BAS GST bookkeeping guide](https://www.ato.gov.au/businesses-and-organisations/preparing-lodging-and-paying/business-activity-statements-bas/goods-and-services-tax-gst/simpler-bas-gst-bookkeeping-guide) (purchases you can't claim GST credits for).

### Why this is a separate step

GST treatment rules (R01–R99) determine the initial GST treatment and set a preliminary `credit_claimable` value and `expected_gst` amount.

A separate eligibility step runs after the treatment rules to apply supplier registration requirements.

This separation:
- Keeps treatment rules focused on the purchased goods or services.
- Avoids duplicating supplier registration checks across individual rules.
- Allows supplier eligibility requirements to be changed centrally without modifying individual treatment rules.
- Ensures expected GST is correctly adjusted before reconciliation.

### Order of checks

Apply the following sequence:

1. **Apply GST treatment rules (R01–R99):** Determine the category-based GST treatment and set the initial `credit_claimable` and `expected_gst` values.
2. **Check supplier GST registration:** Apply a separate check after all treatment rules have run.
3. **Adjust expected GST and credit eligibility:**
   - If the supplier is GST-registered, retain the preliminary `expected_gst` and `credit_claimable` values.
   - If the supplier is not GST-registered, set `expected_gst = 0.00` and `credit_claimable = No`, regardless of the preliminary values.

### Supplier registration rule

A supplier that is not registered for GST cannot charge GST. Therefore, purchases from an unregistered supplier cannot generate a GST credit, and no GST should be expected on the purchase.

For unregistered suppliers:
- Set `expected_gst` to `0.00`.
- Set `credit_claimable` to `No`.
- Retain the resolved `category` and `category_source`.
- Do not change the category-based GST treatment classification.
- Retain all existing quality flags.

The registration check overrides both `Yes` and `Review`:
- Initial `Yes` becomes `No`.
- Initial `Review` becomes `No`.
- Initial `No` remains `No`.

### Handling unknown categories

If a purchase has an unknown category:
- If the supplier is registered, retain `credit_claimable = Review` as assigned by R99.
- If the supplier is not registered, change `credit_claimable` to `No` and set `expected_gst = 0.00`.
- Retain `category = unknown` and `category_source = unknown`.
- Keep the unknown-category quality flag regardless of supplier registration status.

The registration check determines credit eligibility and expected GST but does not resolve missing category information.

### Quality flags

The following conditions should be flagged through the quality checks:

| Condition | Quality flag | Action |
|---|---|---|
| Unknown category | `unknown_category` | Review category mapping and provisional GST treatment. |
| Invoice shows GST but supplier is not registered | `gst_charged_by_unregistered_supplier` | Flag for investigation. Do not allow a GST credit. |

An unregistered supplier's invoice showing GST is a potential invoicing or data error. The engine must not accept the GST amount as claimable simply because it appears on the invoice.

Reconciliation provides an additional check: because `expected_gst` is set to `0.00`, any GST amount shown on the invoice will also be identified as a discrepancy.

### Examples

| Case | Purchase | Category | GST treatment | Supplier registered? | Invoice GST | Expected GST | `credit_claimable` | Flag? |
|---|---|---|---|---|---:|---:|---|---|
| GC-1 | Office supplies | `stationery` | Taxable | Yes | $10.00 | $10.00 | `Yes` | No |
| GC-2 | Office supplies | `stationery` | Taxable | No | $0.00 | $0.00 | `No` | No |
| GC-3 | Basic food | `basic_food` | GST-free | Yes | $0.00 | $0.00 | `No` | No |
| GC-4 | Unclassified purchase | `unknown` | Provisional taxable (R99) | Yes | $10.00 | $10.00 | `Review` | `unknown_category` |
| GC-5 | Unclassified purchase | `unknown` | Provisional taxable (R99) | No | $0.00 | $0.00 | `No` | `unknown_category` |
| GC-6 | Office supplies | `stationery` | Taxable | No | $10.00 | $0.00 | `No` | `gst_charged_by_unregistered_supplier` and reconciliation discrepancy |

### Important distinction

The supplier registration check can override credit eligibility and expected GST, but it does not override category resolution or remove existing quality flags.

For example:
- An unknown-category purchase from an unregistered supplier receives `credit_claimable = No` and `expected_gst = 0.00`, but remains flagged for category review.
- An invoice from an unregistered supplier showing GST receives `credit_claimable = No` and `expected_gst = 0.00`. It is flagged by both the supplier-registration quality check and reconciliation.

This ensures that supplier eligibility, expected GST and data-quality checks remain separate but consistent.

## BAS summary rules

### G1: Total sales

**Definition:** Total value of sales, including taxable, GST-free and input-taxed sales.

**Filter:**
```sql
G1 = SUM(gross_amount)
WHERE transaction_type = 'sale'
```

**Includes:** All sales, regardless of GST treatment, including exports.

**Excludes:** Purchases, loans, and other transactions that are not sales.

**Note:** Amounts are GST-inclusive, consistent with the Calculation Worksheet Method.

### 1A: GST on sales

**Definition:** Total GST payable on taxable sales.

**Filter:**
```sql
1A = SUM(expected_gst)
WHERE transaction_type = 'sale'
AND gst_treatment = 'taxable'
```

**Includes:** GST calculated by the engine for taxable sales, using `expected_gst` as calculated under the Calculation rules.

**Excludes:** GST-free sales, input-taxed sales and purchases.

**Important:** BAS reports the GST liability, not simply the amount the client charged on their invoices. The engine uses calculated GST rather than invoice GST, with any differences handled through reconciliation.

**Rounding note:** The engine sums GST rounded at the individual transaction-line level. As a result, 1A may differ from the worksheet's G9 calculation by a few cents.

### 1B: GST on purchases

**Definition:** GST credits the business can claim on eligible purchases.

**Filter:**
```sql
1B = SUM(expected_gst)
WHERE transaction_type = 'purchase'
AND credit_claimable = 'Yes'
```

**Includes:** Purchases marked `Yes` after GST treatment and supplier registration checks, using `expected_gst` as calculated under the Calculation rules.

**Excludes:** GST-free purchases, input-taxed purchases, purchases from unregistered suppliers, and purchases marked `Review` or `No`.

**Note:** `credit_claimable` is the main filter. This simplified model assumes purchases marked `Yes` also meet other credit requirements, such as business use and holding a valid tax invoice. Private use and apportionment are not modelled.

### Example

All amounts below are GST-inclusive.

| Transaction | Type | Category | GST treatment | Gross amount | Expected GST | Credit claimable |
|---|---|---|---|---:|---:|---|
| Stationery sale | Sale | stationery | Taxable | $1,100.00 | $100.00 | N/A |
| Basic food sale | Sale | basic_food| GST-free | $220.00 | $0.00 | N/A |
| Financial services sale | Sale | financial_services | Input-taxed | $550.00 | $0.00 | N/A |
| Stationery purchase | Purchase | stationery | Taxable | $110.00 | $10.00 | Yes |
| Basic food purchase | Purchase | basic_food| GST-free | $55.00 | $0.00 | No |
| Unknown purchase | Purchase | unknown | Provisional taxable | $110.00 | $10.00 | Review |

**BAS summary:**

- **G1 = $1,870.00** ($1,100 + $220 + $550). All three sales are included, regardless of GST treatment.
- **1A = $100.00**. Only the taxable sale contributes GST.
- **1B = $10.00**. Only the stationery purchase is marked `Yes`. The basic food purchase is excluded because it is GST-free, and the unknown purchase is excluded because it is marked `Review`, not `Yes`.

The unknown purchase still has provisional GST of $10.00 under R99, but it does not contribute to the GST credit total until reviewed.

## Resolved questions

| Rule | Question | Answer | Source |
|---|---|---|---|
| R03/R04 | Is hot roast chicken GST-free? | No. Hot takeaway chicken is taxable and should be categorised as `taxable_food`. | ATO, [Detailed food list](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/detailed-food-list) |
| R03/R04 | Is cold cooked chicken GST-free? | Yes. Cold cooked chicken is generally GST-free and should be categorised as `basic_food`. | ATO, [Detailed food list](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/detailed-food-list) |
| R03/R04 | Is warm fresh bread taxable? | No. Bread that is still warm because it has just been baked is generally GST-free, unless it falls into another taxable food category. | ATO, GST and food (TODO link) |
| R03/R04 | Are hampers containing taxable and GST-free products entirely taxable? | No. A hamper of separate, individually packaged products is generally a mixed supply, with the value apportioned where needed. In the data, a hamper should be split into separate lines, one per product type, each with its own category. | ATO, Mixed GST status on food products (TODO link) |
| R03 | Are snacks, confectionery and soft drinks GST-free? | Many are taxable, e.g. chocolate, lollies, potato crisps and soft drinks. These should be categorised as `taxable_food`. | ATO, [Detailed food list](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-food/detailed-food-list) |
| R05 | Which medical services are GST-free? | Services for which a Medicare benefit is payable, or other services supplied by or on behalf of a medical practitioner or approved pathology practitioner that are generally accepted as necessary for appropriate treatment. | ATO, [Medical services](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-health/medical-services) |
| R05 | Does a medical service always need to be provided by a recognised medical professional? | No. If a Medicare benefit is payable, the service can qualify without meeting the provider requirement in the second test. | ATO, [Medical services](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-health/medical-services) |
| R05 | Which other health services can be GST-free? | Listed services such as physiotherapy, psychology, dentistry and chiropractic, provided by a recognised professional and considered necessary for appropriate treatment. | ATO, [Other health services](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-health/other-health-services) |
| R05 | Are cosmetic procedures GST-free? | Not generally, where no Medicare benefit is payable and the procedure is performed mainly to improve appearance. | ATO, [Medical services](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-health/medical-services) |
| R05 | Are health-related products automatically GST-free? | No. Products sold separately generally follow their own GST rules. Some goods supplied as part of a GST-free health service may qualify if they meet specific conditions. | ATO, GST and health (TODO link) |
| R05 | Is remedial massage GST-free? | Not when supplied on its own. It may qualify when supplied as part of an eligible listed health service, such as physiotherapy. | ATO, [Other health services](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/in-detail/your-industry/gst-and-health/other-health-services) |

## Open questions for a tax SME

| Question | Related rule | Current assumption | Impact if assumption is wrong |
|---|---|---|---|
| Should overseas financial supplies be GST-free under R01 or input-taxed under R02? | R01 / R02 | R01 takes priority when both rules match. | Incorrect GST classification for overseas financial supplies, potentially resulting in incorrect BAS reporting. |
| How should GST credits be apportioned for clients making both taxable and input-taxed sales? | R02 | Assume clients do not make input-taxed sales affecting their GST credit entitlement. | The engine may overstate GST credits on taxable purchases relating to input-taxed supplies. |
| Should unknown categories default to taxable, with credits held for review? | R99 | Unknown categories receive provisional taxable treatment, with purchases set to `Review` for credit eligibility. Pending tax SME approval. | Incorrect assumptions could result in misclassified transactions or incorrect GST credit claims. |
| Do the client's tax codes identify a specific category, or only the GST treatment? | Category resolution | Each tax code maps to a single category in `tax_codes.csv`. | If codes only show treatment (e.g. `GST`, `FRE`), the engine can't tell basic food from medical, and more lines would fall back to the supplier default or `unknown`. |