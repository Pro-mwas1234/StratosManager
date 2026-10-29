# Build Plan — Multi-Tenant Business Management Platform (Kenya SMB)

## 0. Product Summary
A single Python codebase ("KaziBiz / KBZ") that lets Kenyan SMEs run six business types from one
tenant workspace, exposed through four surfaces that all share one service layer:

1. **Modules**: retail (duka POS + stock), hotel (rooms/check-in/out), invoicing (KRA PIN, VAT 16%,
   M-Pesa payment refs), restaurant (tables, menu, kitchen tickets, orders), property rental
   (units, leases, rent collection), manufacturing (BOM, work orders, production runs).
2. **REST API** (FastAPI) — bearer-token auth, per-tenant isolation enforced centrally.
3. **Terminal CLI** (Typer + Rich) — same services, for owners without a browser.
4. **MCP server** (fastmcp) — AI-agent tools; each tool is gated by the same entitlement checks.
5. **SaaS billing/entitlements** — plans (Starter/Growth/Pro), monthly limits, feature flags,
   usage metering, overage → 402 Payment Required.

## 1. Architectural Decisions (and why)
- **Single DB, shared schema, `tenant_id` discriminator.** Cheaper than DB-per-tenant for SMB SaaS;
  isolation is enforced in the repository layer (every query auto-scoped), not in every module.
- **SQLite first, Postgres later.** Storage is behind a thin `Database` gateway so we can swap to
  Postgres (`?` → `%s` placeholders, JSON columns) without touching modules. Zero-dependency start:
  no ORM, hand-rolled migration runner with forward-only SQL files.
- **One service layer, four transports.** HTTP/CLI/MCP only do input parsing + auth context, then
  call `kbz/services/*`. This guarantees parity: if the CLI can do it, the API and MCP can too.
- **Money as integer cents** (KES centi-units) everywhere; format at the edge. No float arithmetic.
- **Entitlement checks are middleware/decorators**, not scattered `if plan == ...` branches:
  `@requires_feature("hotel")`, `check_limit(tenant, "invoices_per_month")`.
- **Determinism for testability:** injectable clock (`now()`), injectable ID generator, seeded demo data.

## 2. Layered Design
```
kbz/
  core/        config, db gateway, migrations, ids, money, time, errors, logging
  domain/      tenant/user/auth context, password hashing (PBKDF2), tokens
  services/    one service per module + shared (stock ledger, payments, documents)
  billing/     plans.yaml-equivalent (python dict), entitlements, usage metering, invoices
  api/         FastAPI app, routers per module, auth dependency, error handlers
  cli/         Typer app mirroring API verbs
  mcp_server/  fastmcp tools wrapping services with agent-friendly schemas
  seed/        demo tenants (duka, hotel, restaurant...) for dev + tests
tests/         pytest: unit (services), integration (TestClient), multi-tenant isolation matrix
data/          runtime sqlite file (gitignored)
```

## 3. Data Model (core tables)
- `tenants(id, name, kra_pin, phone, plan_id, created_at)`
- `users(id, tenant_id NULLABLE, email, pw_hash, role[owner|staff|platform_admin])`
- `tokens(token_hash, user_id, kind[cli|api|mcp], expires_at)`
- `plans(id, price_kes_cents, features(csv), limits_json)`
- `subscriptions(tenant_id, plan_id, status, period_start, period_end)`
- `usage_events(tenant_id, metric, qty, ts)` → aggregated for limit checks
- Module tables (all carry `tenant_id`):
  - retail: `products, stock_levels, sales, sale_items, suppliers, purchase_orders`
  - hotel: `rooms, bookings, stays(check_in/out), housekeeping`
  - invoicing: `customers, invoices, invoice_lines, payments(reference, method=MPESA|CASH|BANK)`
  - restaurant: `menu_items, tables, orders, order_items, kitchen_tickets`
  - property: `properties, units, leases, rent_bills, rent_payments, maintenance_requests`
  - manufacturing: `bills_of_material, components, work_orders, production_runs, raw_stock`
- Shared ledger: `stock_movements(product/sku, delta, reason, ref)` used by retail + manufacturing.

## 4. Billing & Entitlement Rules (v1)
| Plan | Price (KES/mo) | Features | Limits |
|---|---|---|---|
| Starter | 999 | retail OR invoicing | 2 users, 500 docs/mo, 200 products |
| Growth | 2999 | retail+invoicing+restaurant+property | 10 users, 2000 docs/mo |
| Pro | 7999 | all six + MCP + API | unlimited docs, 50 users |
- Enforcement points: login (feature flag), write operations (limit check → 402 + reset date),
  MCP tool list (tools hidden/disabled if unentitled), CLI shows plan banner.
- Metering: every document-producing service writes a `usage_event`; `GET /billing/usage` reports it.

## 5. Kenya-Local Details
- Currency KES, VAT 16% default (zero-rated flag on items), KRA PIN validation format.
- Payment references: M-Pesa shortcode-style alphanumeric (`QGH...`), STK-push placeholder field.
- Phone numbers `+254...` normalized; receipts/invoices printable ASCII (SMS-first culture).

## 6. Build Order (milestones, each independently testable)
- **M1 Core**: config/db/migrations/money/errors + tenant & user CRUD + token auth. *Gate: isolation test.*
- **M2 Billing**: plans, subscriptions, entitlement decorators, usage metering. *Gate: 402 on over-limit.*
- **M3 Invoicing** (chosen first module: exercises customers, lines, VAT, payments, numbering).
- **M4 Retail** (products, stock ledger, POS sale endpoint).
- **M5 Restaurant** (menu, tables, orders → reuses stock ledger on consumption).
- **M6 Hotel** (rooms, bookings calendar, check-in/out).
- **M7 Property** (units, leases, rent schedule, arrears report).
- **M8 Manufacturing** (BOM explosion, work orders, finished-goods receipt via stock ledger).
- **M9 REST API**: mount routers, OpenAPI, request-id logging, error envelope.
- **M10 CLI**: `kbz <module> <verb>` table output, `login`, `whoami`, `--json`.
- **M11 MCP**: tools per module (`kbz_list_products`, `kbz_create_invoice`, ...) + resource for tenant summary.
- **M12 Seed + Docs + Test sweep**: demo tenants, README, smoke script.

## 7. Testing Strategy
- Unit: money math, VAT rounding, BOM explosion, limit windows.
- Integration: FastAPI TestClient happy paths + 401/402/403/404/409.
- **Isolation matrix**: two tenants × every write/read endpoint → cross-tenant access must fail.
- Parity test: same action via API and service yields identical DB state.

## 8. Risks / Mitigations
- Scope creep across 6 modules → strict v1 verb set per module (list/create/post/report).
- Tenant leakage → single repository chokepoint + mandatory isolation CI test.
- SQLite concurrency → WAL mode, short transactions; documented Postgres upgrade path.
- MCP prompt injection into writes → confirmation-required flag on destructive tools.

## 9. Definition of Done (this session)
All milestones compile and pass `pytest`; server starts; CLI runs against live DB; MCP server lists
tools; seeded demo tenant usable end-to-end (invoice a duka sale, check a hotel guest in).
