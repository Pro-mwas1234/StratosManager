-- 0005 restaurant module
CREATE TABLE IF NOT EXISTS menu_items(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT,
  price_cents INTEGER NOT NULL DEFAULT 0, available INTEGER NOT NULL DEFAULT 1,
  product_id TEXT, created_at TEXT NOT NULL, updated_at TEXT);

CREATE TABLE IF NOT EXISTS tables(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, label TEXT NOT NULL, seats INTEGER NOT NULL DEFAULT 4,
  status TEXT NOT NULL DEFAULT 'free', created_at TEXT NOT NULL, updated_at TEXT,
  UNIQUE(tenant_id, label));

CREATE TABLE IF NOT EXISTS orders(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, ticket_no TEXT NOT NULL, table_id TEXT,
  status TEXT NOT NULL DEFAULT 'open', total_cents INTEGER NOT NULL DEFAULT 0,
  service_charge_cents INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT,
  UNIQUE(tenant_id, ticket_no));

CREATE TABLE IF NOT EXISTS order_items(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, order_id TEXT NOT NULL, menu_item_id TEXT NOT NULL,
  qty INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL, line_total_cents INTEGER NOT NULL,
  notes TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_orderitems ON order_items(tenant_id, order_id);
