# KaziBiz REST API Contract v0.2 (frozen for the Android app)

Base URL (dev): `http://10.0.2.2:8000` (emulator → host). All requests after login carry
`Authorization: Bearer <token>`. Money is always **integer cents** (`*_cents` fields); never floats.

## Auth flows
- `POST /auth/register` — body `{email, password(≥8), tenant_name, kra_pin?, phone?, plan_id?}` →
  `{user:{id,email,role,tenant_id}, token}`. Creates tenant + owner. Token kind=`api`.
- `POST /auth/login` — `{email,password}` → `{token,user_id,email,role,tenant_id,tenant_name,plan,plan_name,features[]}`.
  The app persists token in EncryptedSharedPreferences and `features` drives nav gating.
- `GET /auth/session` — resume check on app start → `{valid,user_id,email,role,tenant_id,tenant_name,plan}` or 401.
- `POST /auth/logout` — revokes the presented token server-side.
- `POST /auth/staff` (owner only) — `{email,password}` → staff user; counts against `users` limit.
- `GET /me` — `{user{...}, tenant{id,name,kra_pin,phone}, plan{id,name,features[]}}`.

## Error envelope (stable — maps 1:1 to Kotlin `AppError`)
```json
{"error": {"code": "<machine code>", "message": "...", "details": {}}}
```
Machine codes are snake_case and stable — Kotlin `AppError.Code` maps exactly:

| HTTP | `error.code` | meaning / app behaviour |
|------|--------------------|---------------------------------------------|
| 401  | `unauthenticated`    | token missing/expired/revoked → force re-login |
| 403  | `forbidden`          | feature not in plan or role guard → show lock badge (`details.feature`, `details.plan`) |
| 404  | `not_found`          | row absent **or owned by another tenant** (isolation is silent) |
| 409  | `conflict`           | stock, duplicate SKU, overlap booking, double-pay → inline error on the form |
| 402  | `payment_required`   | plan meter exceeded → open UpgradeSheet (`details.metric`, `details.limit`, `details.used`) |
| 422  | `validation_error`   | bad input → highlight fields from `details` |
| 500  | `internal_error`     | unexpected → snackbar + log |

## Idempotency & pagination
- All `POST`s (except `/auth/register`) accept header `Idempotency-Key: <uuid>`; a replayed key returns the
  stored response verbatim with header `X-Idempotent-Replay: true`. The offline outbox MUST send unique keys.
- List endpoints support `limit`; add `updated_since=YYYY-MM-DDTHH:MM:SSZ` where noted for delta sync.

## Dashboard (Home screen = one call)
- `GET /dashboard` → `{generated_at, tenant{plan_id,plan_name,features}, usage{...}, retail{today_sales_count,
  today_total_cents,today_total_fmt,low_stock_count}, invoicing{open_invoices,receivable_cents,receivable_fmt},
  restaurant{open_orders}, hotel{arrivals_today,departures_today,in_house,occupancy_pct},
  property{unpaid_bills,arrears_cents,arrears_fmt}, manufacturing{work_orders_open}}`
  — sections appear only for entitled modules.

## Retail (feature `retail`) — POS flagship
- `GET /retail/products` → list incl. `stock_qty` · `POST /retail/products` `{sku,name,sale_price_cents,cost_price_cents?,category?,vat_exempt?,reorder_level?}`
- `GET /retail/products/{id}` · `POST /retail/products/{id}/stock` `{delta,reason?,ref?}` → `{movement_id,on_hand}` (409 if negative)
- `GET /retail/stock/low` · `GET /retail/sales` · `POST /retail/sales` `{items:[{product_id,qty}],payment_method(CASH|MPESA|CARD),mpesa_ref?,cashier?}`
  → `{id,receipt_no,total_cents,total_fmt,items}` · `GET /retail/summary/today`

## Invoicing (feature `invoicing`)
- `GET/POST /invoices/customers` `{name,email?,phone?,kra_pin?,address?}`
- `GET /invoices/?status=open|partially_paid|paid|void` (alias of issued) · `POST /invoices/`
  `{customer_id?,lines:[{description,qty,unit_price_cents,vat_rate}],due_date?,notes?,inclusive_vat?}` → invoice+lines+payments
- `GET /invoices/{id}` · `POST /invoices/{id}/payments` `{amount_cents,method,reference?}` · `POST /invoices/{id}/void` (owner)
- `GET /invoices/reports/aging` → `{as_of,open_invoices,buckets_cents{current,overdue_1_30,overdue_31_60,overdue_60_plus}}`

## Restaurant (feature `restaurant`)
- `GET/POST /restaurant/menu` `{name,price_cents,category?,product_id?}` · `GET/POST /restaurant/tables` `{label,seats}`
- `GET /restaurant/orders?status=open|closed` · `POST /restaurant/orders` `{table_id?}`
- `GET /restaurant/orders/{id}` · `POST /restaurant/orders/{id}/items` `{menu_item_id,qty,notes?}`
- `POST /restaurant/orders/{id}/close` `{payment_method}` · `GET /restaurant/orders/{id}/kitchen-ticket` → `{ticket:"..."}`

## Hotel (feature `hotel`, Pro)
- `GET/POST /hotel/rooms` `{number,rate_cents,room_type}` · `GET /hotel/availability?check_in=&check_out=`
- `GET /hotel/bookings?status=` · `POST /hotel/bookings` `{guest_name,guest_phone?,room_id,check_in,check_out}` (409 overlap)
- `GET /hotel/bookings/{id}` · `POST .../check-in` · `POST .../check-out` · `POST .../cancel`
- `GET /hotel/reports/occupancy?date=` → `{total_rooms,occupied,occupancy_pct}`

## Property (feature `growth+`)
- `GET/POST /property/properties` `{name,location?}` · `POST /property/units` `{property_id,label,rent_cents}`
- `GET /property/leases?status=active|ended` · `POST /property/leases` `{unit_id,tenant_name,tenant_phone?,start_date,end_date,rent_cents?,deposit_cents?}`
- `POST /property/leases/{id}/end` · `POST /property/rent-bills` `{lease_id,period?(YYYY-MM),due_day?}` · `GET /property/rent-bills/{id}`
- `POST /property/rent-bills/{id}/payments` `{amount_cents,method,reference?}` · `GET /property/reports/arrears`

## Manufacturing (feature `pro`)
- `GET/POST /manufacturing/boms` `{product_id,components:[{product_id,qty}],version?}` · `GET /manufacturing/boms/{id}` · `GET /manufacturing/boms/{id}/explode?qty=`
- `GET /manufacturing/work-orders?status=planned|in_progress|done` · `POST /manufacturing/work-orders` `{bom_id,qty_planned,notes?}`
- `POST /manufacturing/work-orders/{id}/start` (consumes components) · `POST .../complete` `{qty_produced}` (adds finished stock)

## Billing
- `GET /billing/plans` · `GET /billing/usage` (meters vs limits) · `POST /billing/subscribe` `{plan_id}`
- Any 402 anywhere → app shows UpgradeSheet; any 401 → re-login flow.

## Seed fixtures (demo tenants for QA/A11)
`python -m kbz.seed.seed` creates: **Mama Mboga Duka** (starter, retail+invoicing, POS-ready products),
**Nairobi Bites** (growth, restaurant), **Nakuru Lodge** (pro, hotel), **Rift Valley Apartments** (pro, property),
**Juba Steelworks** (pro, manufacturing). Password for all demo users: `demo1234pass`.
