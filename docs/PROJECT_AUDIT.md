# Urban Furniture project audit

Audit date: 20 September 2026

Source requirements: `Urban Furniture Accounting System.pdf` (six pages). The attachment was used only as a product specification.

## Delivery result

The application implements the complete accounting workflow described in the source: master data, purchasing, sales, invoice and bill conversion, payments, double-entry journals, analytics, budgets, stock, Balance Sheet, Profit and Loss, and Budget reporting. The implementation adds Indian GST handling, role-specific workspaces, payment approval, expenses, activity history, data import/export, backup, dark/light themes, a professional printable invoice, and authenticated live refresh.

## Architecture

| Layer | Technology | Responsibility |
|---|---|---|
| Web interface | Next.js 16, React 19, Tailwind CSS 4, Lucide icons | Responsive role-based interface and printable invoice |
| API | Python 3.12+, Flask 3 | Authentication, permissions, validation, calculations, workflows and reports |
| Database | PostgreSQL with psycopg | Durable multi-user records, constraints, accounting data and live revision triggers |
| Live updates | Authenticated server-sent events | Announces a revision only; each browser reloads its own permitted data |
| Hosting | Two Vercel projects from one repository | Next.js frontend and Flask API |
| Cloud data | Vercel Marketplace PostgreSQL provider | Hosted relational database with TLS and pooled connections |

All monetary values are stored as integer paise. The API recalculates subtotals, tax and totals rather than trusting browser amounts.

## Requirement coverage

| Requirement group | Delivered behavior | Main interface |
|---|---|---|
| Contacts | Customer/vendor/both, address, state, GSTIN, contact details, image and portal user | Contacts |
| Products | Goods/service/combo, SKU, HSN/SAC, unit, sale price, cost and reorder level | Products, Inventory |
| Chart of accounts | Asset, Liability, Expense, Income and Capital accounts with protected system accounts | Accounting |
| Journals | Sales, Purchase, Cash, Bank and General with default accounts | Accounting |
| Journal entries | Balanced manual entries and automatic postings for documents, tax, payments and expenses | Accounting, Activity |
| Purchases | Multi-line purchase order, vendor bill conversion, receipt of goods and cash/bank payment | Orders, Documents, Payments |
| Sales | Multi-line sales order, customer invoice conversion, stock issue and cash/bank receipt | Orders, Documents, Payments |
| GST | Intra-state CGST/SGST, inter-state IGST and exempt mode, calculated and posted in the backend | Orders, Invoice, Reports |
| Analytics and budgets | Income/expense analytic accounts, date periods, owner, planned value, actual and variance | Accounting, Reports |
| Reports | Date-filtered Balance Sheet, Profit and Loss, Budget, ledger and stock | Reports |
| Roles | Owner, accountant and contact permissions enforced by the API | Role-specific navigation and dashboard |

Detailed one-to-one evidence is maintained in `docs/REQUIREMENTS.md`.

## End-to-end business rules

1. A purchase order remains a draft and has no ledger or stock effect.
2. Converting it to a vendor bill receives goods, records purchase expense and input GST, and creates the payable.
3. A cash or bank payment reduces the payable and creates a balanced journal entry.
4. A sales order remains a draft and has no ledger or stock effect.
5. Converting it to an invoice issues goods, records sales and output GST, and creates the receivable.
6. A receipt reduces the receivable and creates a balanced journal entry.
7. Posted documents preserve seller, buyer, HSN, unit, description, price and tax snapshots so later master edits do not rewrite history.
8. Contact users can see only records linked to their own contact. Their payment submissions require staff approval before posting.

## Security and data integrity

- Passwords use Werkzeug salted hashes; the database does not store plain-text passwords.
- Every modifying API request requires a session-bound CSRF token.
- Session cookies are HTTP-only, SameSite Strict and Secure in production.
- API authorization is enforced on the server for every role.
- Security headers deny framing, restrict content sources and prevent MIME sniffing.
- Upload size and supported image formats are restricted.
- Database constraints, transactions and advisory locks protect accounting and sequence updates.
- CSV export neutralizes spreadsheet-formula prefixes.
- Vercel startup fails clearly when the cloud database or signing secret is missing, avoiding temporary local data.

## Deployment model

The repository deploys as two Vercel projects because the applications have different runtimes:

1. **Urban Furniture API** uses the repository root and detects `app.py` as Flask.
2. **Urban Furniture Web** uses `Frontend` as its root and detects Next.js.
3. The frontend receives `URBAN_BACKEND_URL` and proxies `/api/*` to the API. Browser cookies therefore remain same-origin.
4. The API receives `DATABASE_URL`, `URBAN_SECRET` and `URBAN_HTTPS=1`.
5. A PostgreSQL integration such as Neon or Supabase must be connected through the Vercel Marketplace. The database should be located near the functions and use a pooled TLS URL.

The API creates and upgrades its schema on startup. Run `python scripts/seed_demo.py` once against the hosted database if the public demonstration accounts and three demonstration workflows are required.

## Verification gates

- Backend accounting and authorization suite: `python -m unittest discover -s tests`
- Frontend production compilation: `npm run build` in `Frontend`
- Deployment health: `/api/session` returns JSON through the frontend domain
- Role smoke tests: owner, accountant and contact login and land on their allowed workspace
- Financial smoke test: create order, post invoice, record payment, then confirm ledger and report balances

## Operational limits

- Cash and bank are accounting methods; no external payment gateway was specified.
- Combo products are treated as whole items because the source does not define a bill of materials.
- Posted records are immutable. Corrections require a future credit-note, debit-note or reversal workflow.
- The live stream reconnects automatically after a Vercel function duration limit. PostgreSQL remains the source of truth.
- Production backups, retention periods, custom domains, email delivery and monitoring policies must be chosen by the system owner.
