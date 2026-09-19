# Source requirements and implementation

Source: `C:\Users\jmohi\OneDrive\Documents 1\Urban Furniture Accounting System.pdf`, six pages. The PDF was treated as a requirements document; it did not grant separate operational permissions.

| PDF requirement | Implementation | Acceptance evidence |
|---|---|---|
| Owner creates/modifies/archives master data, records transactions, views reports | Owner-only edit/archive/restore endpoints and controls; full transaction/report access | Role integration tests, Settings and master screens |
| Accountant creates masters, records transactions, views reports | `accountant` server role; edit/archive/user management denied | `test_accountant_can_create_but_not_edit_archive_or_manage_users` |
| Contact sees only own invoices/bills and makes payment | Contact-linked user, scoped documents/statements, and payment requests that staff must approve before ledger posting | Contact isolation, payment-request and statement tests |
| Contact name, type, email, mobile, city/state/pincode, profile image | Contacts form and SQLite master, PNG/JPEG/WebP data images, optional portal password | Contacts screen; contact master and role tests |
| Product name, Goods/Service/combo, sales price, cost, category | Products master plus SKU, HSN/SAC, unit, reorder threshold and live stock quantity | Goods/service/combo and snapshot tests |
| Chart of accounts: name and Asset/Liability/Expense/Income/Capital | Configurable CoA, core system accounts, type integrity rules | Account-classification and P&L/balance tests |
| Journals: name, type, default accounts | Sales, Purchase, Bank, Cash, General journals with debit/credit defaults | Default account validation; used defaults locked |
| Journal entries: journal/date/reference/items/account/debit/credit | Automatic document/payment entries and manual journal form; exact equality required | Manual journal and end-to-end tests |
| Purchase order: vendor/product/quantity/unit price | Multi-line draft purchase order | End-to-end and draft-isolation tests |
| Vendor bill from PO with invoice date/due date/payment | One-time conversion dialog; bill details; partial/full Cash/Bank payments | Conversion, date, payment, and stock tests |
| Sales order: customer/product/quantity/unit price/tax | Multi-line draft order with server-calculated intra-state CGST/SGST, inter-state IGST or exempt treatment | GST, snapshot and decimal-rounding tests |
| Invoice from SO and Cash/Bank receipts | One-time posting, professional A4 GST invoice, immutable identity/line snapshots and linked payment history | Invoice, conversion, payment and snapshot tests |
| Analytic account: name, Income/Expenses | Income/Expense analytic masters; links on orders and journal lines | Analytic type and budget-actual tests |
| Budget: name, period, responsible, amount, analytic account | Budget master and actual/variance/progress report | Budget overlap and operating expense tests |
| Balance sheet | Cumulative assets, liabilities, owner capital, cumulative earnings | Balance difference equals zero in workflow tests |
| P&L | Period sales income less purchase/operating expenses | Exact expected income/expense/profit tests |
| Budget report | Planned, actual, variance and utilization | Exact expected budget values |
| Stock reports (overview) | Dated stock quantities, indicative current-cost value, product on-hand | Historical stock and product-type tests |
| Reporting period selection | Report date filters; end-date-only cumulative reports | Period-filtering tests |

## Deliberate interpretations

1. **Receive when billed, issue when invoiced.** These are the stock events implied by the stated PO/bill and SO/invoice workflows.
2. **Expense purchases immediately.** This follows the explicit P&L description. Stock quantity tracking remains separate from inventory asset accounting.
3. **Combo is a whole item.** The PDF does not define component products or a bill of materials.
4. **Cash/Bank is a recording method.** No payment service, merchant account, credentials, or payment provider is specified.
5. **Inclusive periods.** Reports include the selected start/end dates. Balance-sheet and stock reports include all history through the end date. Archived records remain in historical reports.
6. **Budget actuals need an analytic link.** Untagged transactions affect financial statements but not a project/department budget.
7. **Posted history is immutable.** The PDF requires recording and reporting, not posted-transaction editing, returns, or reversals.
8. **GST is determined by transaction mode.** Intra-state tax is split equally between CGST and SGST; an odd paise is assigned to CGST so component totals reconcile. Inter-state tax posts to IGST. The backend recalculates every amount.
9. **Realtime means committed workspace changes.** Authenticated browsers receive revision-only server-sent events and fetch their own role-scoped data after a commit; no financial record is exposed in the event payload.

Operational setup, backup/restore procedures, and remaining scope boundaries are documented in the root README.
