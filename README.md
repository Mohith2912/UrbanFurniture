# Urban Furniture Business OS

A complete accounting, sales, purchasing and inventory prototype built from `Urban Furniture Accounting System.pdf`. It runs as a responsive Flask web application with a transactional PostgreSQL backend, realtime browser updates, server-calculated GST and professional printable invoices. The active workspace contains no sample customers, products, orders, invoices, payments, expenses or budgets.

## Run on Windows

PostgreSQL 17 is installed natively for this workspace. Docker is not used.

```powershell
cd E:\UrbanFurniture
.\start.ps1
```

`start.ps1` creates a Python virtual environment, installs dependencies, starts the private loopback PostgreSQL service when present, and serves the site at **http://127.0.0.1:5050**. The existing owner and accountant accounts were preserved during migration.

For a hosted database, place the provider's PostgreSQL connection string in `.env`:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Keep `.env` private. The app creates and migrates its schema at startup. Use an empty hosted database for the first migration; `scripts/migrate_to_postgres.py` refuses to overwrite a database that already contains users.

## What is included

- Owner, accountant and customer/vendor portal roles with server-side access control, CSRF protection, account disabling and password management.
- Customer and vendor masters with GSTIN and address fields; products with SKU, HSN/SAC, unit, reorder level, prices and type.
- Purchase orders, vendor bills, sales orders, tax invoices, stock receipt/issue and Cash/Bank payments.
- Double-entry posting, protected control accounts, manual journals, analytic accounts and budgets.
- Operating expenses with automatic ledger and budget posting.
- Payment requests from contacts, followed by staff approval or rejection; portal users cannot post money directly.
- Realtime updates between open browsers through authenticated server-sent events backed by a database revision.
- Receivable ageing, upcoming cash forecast, low-stock alerts, reorder action, contact statements and dashboard trends.
- Atomic CSV preview/import for products and contacts, safe CSV exports, print layouts and application-level backups.
- P&L, balance sheet, budget, stock and general-ledger reports with date filters.

## GST invoices

Invoice totals are calculated again on the server; browser values are only previews. Monetary values are stored as integer paise and line tax uses `Decimal` round-half-up.

- Intra-state documents split tax into CGST and SGST and post each component to its own input/output ledger account.
- Inter-state documents calculate IGST.
- Exempt documents calculate no GST.
- Posted invoices retain immutable seller, buyer, line, HSN/SAC, unit, place-of-supply and tax snapshots.
- The printable A4 invoice includes company and buyer identity, GSTIN, document and due dates, line-level taxable values, tax-rate columns, totals, amount in words, payment status, bank details, terms and signature area.
- When a one-paise tax split is unavoidable, CGST receives the extra paise and `CGST + SGST` always equals total GST.

Configure the legal company identity, GSTIN, state, bank details, invoice note and terms in **Settings → Company profile** before issuing invoices. Tax rates and place of supply remain business inputs; have an accountant validate the configuration for the company's registrations and filing obligations.

## First-use workflow

1. Complete the company profile.
2. Add vendor and customer contacts, including GST details where applicable.
3. Add products with SKU, HSN/SAC, unit, price, cost and reorder level.
4. Create and post a purchase order to receive stock and generate a vendor bill.
5. Create and post a sales order to issue stock and generate a GST invoice.
6. Record Cash/Bank settlements or review contact payment requests.
7. Use Reports, Statements, Expenses and the action dashboard to operate the workspace.

## Accounting behavior

- Currency is INR. Money is stored in paise; quantities support three decimal places.
- Purchases are expensed when billed, matching the source specification. Stock quantity is tracked separately and indicative stock value uses current product cost.
- Goods and combos move stock as whole items; services do not. Sales posting cannot create negative stock on the posting date or later historical dates.
- Drafts can be cancelled and converted once. Posted documents, entries and payments are immutable.
- Receivable/payable control accounts are protected from manual entries.
- Reports include the chosen endpoints. Balance sheet and stock are cumulative through the end date; P&L and ledger use the selected period.
- Payment screens record accounting settlements; no bank or payment-gateway transfer is performed.

## Database and backups

The active local database is PostgreSQL on `127.0.0.1:55432`. Its generated credentials are stored only in ignored files under `data/`; the previous SQLite database remains as a migration safety copy. A pre-clean snapshot is available under `data/backups/`.

The owner backup button creates a private application-data export on PostgreSQL. For disaster recovery, also schedule provider snapshots or PostgreSQL `pg_dump` backups. Backups include user password hashes and financial data and must be stored securely.

Supported environment settings:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | native PostgreSQL configured in `.env` | PostgreSQL connection string |
| `URBAN_DB` | `data/urban.sqlite3` fallback | SQLite path when no `DATABASE_URL` exists |
| `PORT` | `5050` | HTTP port |
| `URBAN_HOST` | `127.0.0.1` | Listen address |
| `URBAN_SECRET` | persisted `data/.secret` | Optional session signing secret |
| `URBAN_HTTPS` | unset | Set to `1` behind HTTPS for secure cookies |

## Validation

```powershell
python -m unittest discover -s tests -v
$env:URBAN_TEST_POSTGRES=(Get-Content data\native-database-url -Raw).Trim()
python -m unittest discover -s tests -v
node --check static/app.js
node --check static/workspace.js
```

The 44-test integration suite passes on both SQLite and PostgreSQL. It covers role boundaries, purchase/sale/payment lifecycles, concurrent payment protection, inventory invariants, double-entry rules, reports, budgets, expenses, realtime revisions, imports, statements, CGST/SGST/IGST, tax rounding and immutable invoice snapshots.

## Main files

| File | Purpose |
|---|---|
| `app.py` | Core schema, permissions, posting engine, API and reports |
| `database.py` | SQLite/PostgreSQL adapter |
| `live.py` | Realtime, GST, imports, statements, insights and workspace extensions |
| `static/app.js` | Core browser workflows |
| `static/workspace.js` | Enhanced dashboard, invoices and realtime interface |
| `static/style.css`, `static/workspace.css` | Responsive and print design |
| `scripts/setup_native_postgres.py` | Native PostgreSQL initialization/startup |
| `scripts/migrate_to_postgres.py` | Safe one-time SQLite to PostgreSQL migration |
| `docs/REQUIREMENTS.md` | Source-requirement traceability |

The linked Excalidraw mockup in the PDF was unavailable, so the visual system was designed independently from the documented workflows.

## PeoplePay360-inspired workspace layer

The role experience now follows the PeoplePay360 conventions: an enterprise sidebar and top bar, role-aware navigation, separate workspace context for the owner/admin, accountant and partner/contact roles, and a persistent light/dark theme preference. The accounting service remains Flask/PostgreSQL because that is where the verified ledger, GST and invoice rules live; the shared shell is implemented without changing those financial APIs.

## Next.js frontend

The primary frontend lives in `Frontend/` and follows the PeoplePay360 client stack: Next.js App Router, React, Tailwind CSS 4, Lucide icons and a same-origin API rewrite to the accounting service. It provides separate protected routes for the dashboard, contacts, products, inventory, sales and purchases, invoices and bills, expenses, payments, payment approvals, accounting, reports, activity and settings. The shared workspace provider loads the authenticated session, enforces role-aware navigation and refreshes live data through server-sent events.

```text
Frontend/src
├── app
│   ├── (workspace)          Protected application routes and shared layout
│   ├── login               Sign-in route
│   ├── globals.css         Responsive UI and printable invoice design
│   └── layout.jsx          Root document layout
├── components
│   ├── app-shell.jsx       Sidebar, header, theme and role navigation
│   ├── workspace-provider.jsx  Session, live data and realtime refresh
│   ├── page-ui.jsx         Shared panels, dialogs and form feedback
│   ├── master-page.jsx     Contact and product workflows
│   └── invoice-view.jsx    GST invoice, payment and print workflow
└── lib
    ├── api.js              CSRF-aware API client
    ├── format.js           INR and date formatting
    └── navigation.js       Route and role definitions
```

```powershell
cd E:\UrbanFurniture\Frontend
npm install
npm run dev
```

The Next.js interface runs at `http://127.0.0.1:3000` while Flask provides the accounting API on port `5050`. Set `URBAN_BACKEND_URL` when the backend is hosted elsewhere. The Flask-rendered interface on port `5050` remains available as a fallback and compatibility interface.

For a one-command Windows launch of the Next.js interface and backend, run `E:\UrbanFurniture\start-next.ps1`.

## Demo workspace

Run `python scripts/seed_demo.py` to create or restore the three role accounts shown on the login page. The script also creates three repeatable demonstrations: a GST vendor purchase that receives stock, a GST customer sale with a partial payment, and a paid showroom expense. It is safe to run again because named demo records and completed workflows are reused.
