# Build Plan v2 — StratosManager (StratosManager): Python API backend + Android (Kotlin) mobile app

> **Change from v1:** the terminal CLI (`kbz/cli`) is **dropped**. The primary user surface is now a
> native **Android app in Kotlin** that talks to the existing FastAPI REST API. The MCP server stays
> (it serves AI agents, not humans). One decision per capability: **business logic lives only in the
> Python service layer**; the app is a thin client of the REST contract.

## 0. What already exists (verified against `kbz/`)
- Multi-tenant core: SQLite gateway with tenant-scoped repository chokepoint, migrations 0001–0008,
  integer-cents KES money, PBKDF2 passwords, bearer tokens (`kind=api|cli|mcp`).
- Billing/entitlements: plans starter/growth/pro, feature flags, monthly limits → HTTP 402, usage metering.
- Six modules implemented as services + FastAPI routers: `/invoices`, `/retail`, `/restaurant`,
  `/hotel`, `/property`, `/manufacturing`, plus `/auth`, `/billing`, `/me`, `/health`.
- MCP server wrapping the same services.

## 1. Target architecture
```
┌─────────────────────────────┐        HTTPS + Bearer token
│ Android app (Kotlin)        │  ─────────────────────────────▶  FastAPI (uvicorn)
│ Jetpack Compose + Material3 │                                 kbz/api  ──▶  stratos/services/* (only
│ Hilt DI · Room offline cache│                                        ▲      place business rules
│ Retrofit + kotlinx.serialization│                                   │   live)
└─────────────────────────────┘                            kbz/core/db → SQLite (WAL), later Postgres
        AI agents ──▶ MCP server (unchanged)
```
Principles:
- **Server-enforced entitlements.** The app *renders* plan state (locked tabs, upgrade sheets) but the
  API is the authority; the app must handle 401 (re-auth), 402 (upgrade prompt), 403 (role), 409 (conflict).
- **Mobile-first verbs.** The Kenyan duka owner is often offline → reads cached in Room, writes queued
  and replayed (idempotency keys).
- **Money on the wire = integer cents**, formatted at the edge with `NumberFormat` (`Ksh 1,250.50`).

## 2. Repo layout
```
kbz/                 Python backend (as today; cli/ removed)
  api/  billing/  core/  mcp_server/  seed/  services/
android/             Gradle project (new)
  app/src/main/java/ke/stratosmanager/app/
    data/remote/     Retrofit API interfaces + DTOs (@Serializable)
    data/local/      Room entities/DAOs + DataStore (session)
    data/repo/       Repositories = single source of truth (network-first, Room cache)
    domain/          Models, use cases, PlanGate rules mirroring server features
    di/              Hilt modules
    ui/              Compose: auth/, home/, retail/, invoicing/, restaurant/, hotel/, property/,
                     manufacturing/, billing/, common/ (theme, money fmt, error mapping)
  keystore/ build scripts flavors: debug | staging | release
docs/API-CONTRACT.md frozen REST contract for the app team
```

## 3. REST contract adjustments before app work starts (backend tasks)
1. **CORS middleware** (allow emulator `http://localhost:*` / custom scheme origins).
2. **Auth hardening:** `POST /auth/login` returns `{token, user_id, tenant_id, tenant_name, plan, role}`;
   add `POST /auth/logout` (token revoke) and `GET /auth/session` (app resume check).
3. **Error envelope is stable:** `{error:{code,message,details}}` with codes `AUTH, FORBIDDEN, NOT_FOUND,
   CONFLICT, LIMIT, VALIDATION` → mapped 1:1 to `AppError` sealed class in Kotlin.
4. **Dashboard endpoint:** `GET /dashboard` → per-module counters (today's sales, open orders, arrivals,
   arrears total, WIP work orders) so Home screen is one call.
5. **Idempotency:** accept `Idempotency-Key` header on all POSTs (offline queue replays safely).
6. **Pagination + since-param:** `?limit=&offset=&updated_since=` on list endpoints (mobile bandwidth).
7. Remove `kbz/cli/`, drop `cli` mentions from PLAN.md/README, keep `tokens.kind` values.

## 4. Android app design
### 4.1 Screens & module mapping
| Screen | Endpoints | Notes |
|---|---|---|
| Register / Login / Tenant setup | `/auth/register`,`/auth/login`,`/me` | email+password, KRA PIN optional, plan picker |
| Home dashboard | `/dashboard` | cards per entitled module; 402 banner if trial over limit |
| Retail POS | `/retail/products,/sales,/stock/low,/products/{id}/stock` | product grid → cart → checkout (CASH/M-Pesa ref); low-stock badge |
| Invoicing | `/invoices/*` | customer pick, line builder, VAT toggle, record payment w/ M-Pesa ref, aging report chart |
| Restaurant | `/restaurant/*` | table map, open order, add items, kitchen ticket view (print/share), close w/ payment |
| Hotel | `/hotel/*` | availability date-range picker, bookings list, check-in/out swipe actions, occupancy |
| Property | `/property/*` | units/leases, issue rent bill, record payment, arrears red-list |
| Manufacturing | `/manufacturing/*` | BOM list/explode, work order kanban (planned→in-progress→done) |
| Billing/Plan | `/billing/plans,/usage,/subscribe` | usage meters vs limits, upgrade sheet (M-Pesa STK-push placeholder) |
| Settings | `/auth/session`,`/auth/logout` | server URL (dev/staging/prod), switch account, cache size, clear |

### 4.2 Tech stack (opinionated, boring)
- Kotlin 2.x, **Jetpack Compose + Material 3**, minSdk 26 / target 35, single module first.
- Hilt (DI), Navigation-Compose (type-safe routes via `@Serializable` objects).
- Retrofit 2 + OkHttp (logging/bearer interceptor) + kotlinx.serialization.
- **Room** cache per entity (products, invoices, orders, bookings, leases…) + **WorkManager** sync worker
  replaying the outbox queue; `NetworkMonitor` drives connectivity state.
- DataStore (Preferences) for token/server URL; tokens in **EncryptedSharedPreferences**.
- Coil for images (product photos later), Vico or Canvas for dashboard charts.
- Testing: JUnit + Turbine/CoroutinesTest, MockWebServer for API, Compose UI tests for POS happy path.

### 4.3 Cross-cutting behaviors
- Money: `Long` cents everywhere; `fun kes(cents: Long): String` using `Locale("en","KE")`.
- Errors: `ApiResult<T>` sealed (`Ok/Api(AppError)/Network/Cached`) → snackbar vs upgrade-sheet vs retry.
- Entitlement UX: `PlanGate(feature)` hides/locks nav items; any 402 anywhere opens `UpgradeSheet`.
- Roles: staff sees POS/orders screens only; owner sees billing/staff management.
- Security: no plaintext token, cert pinning for prod flavor, auto re-login flow on 401.

## 5. Milestones (each independently testable)
- **A1 Backend prep:** remove CLI, CORS, session/logout, `/dashboard`, idempotency, OpenAPI snapshot → gate: pytest green + `openapi.json` committed.
- **A2 Contract doc + codegen decision:** freeze `docs/API-CONTRACT.md`; optionally `kotlinx-rpc`/OpenAPI-generated interfaces. Gate: every screen above has listed endpoints + example payloads.
- **A3 App skeleton:** Gradle project, theme, nav graph, login/register wired to real API (MockWebServer tests). Gate: end-to-end signup→login→/me on emulator.
- **A4 Retail POS** (flagship, most-used): products, cart, sale, stock adjust, low stock + Room cache/offline queue. Gate: offline sale created while airplane mode replays on reconnect.
- **A5 Invoicing** + payments (M-Pesa ref) + aging.
- **A6 Restaurant** (tables/orders/kitchen ticket).
- **A7 Hotel** (availability/bookings/check-in-out).
- **A8 Property** (leases/rent bills/arrears).
- **A9 Manufacturing** (BOM/work orders).
- **A10 Billing UX:** plans, usage meters, subscribe, 402 handling polish.
- **A11 Device QA:** small-phone (5''), dark mode, slow-network throttling, demo-seeded tenants (duka/hotel/etc.), Play-store prep (icons, privacy policy stub, signing).

## 6. Risks / mitigations
- Offline write conflicts → idempotency keys + server-side uniqueness (invoice numbers already sequenced).
- Scope creep across 6 modules → ship A3–A5 first (POS+invoicing = 80% of SME daily use), rest behind nav flags.
- Emulator↔host networking → default base URL `http://10.0.2.2:8000`, editable in Settings.
- Token security → EncryptedSharedPreferences, short-lived tokens, logout revokes server-side.
