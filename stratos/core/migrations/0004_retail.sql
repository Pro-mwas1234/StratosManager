-- 0004 retail + shared stock ledger
CREATE TABLE IF NOT EXISTS products(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, sku TEXT NOT NULL, name TEXT NOT NULL,
  category TEXT, sale_price_cents INTEGER NOT NULL DEFAULT 0, cost_price_cents INTEGER NOT NULL DEFAULT 0,
  vat_exempt INTEGER NOT NULL DEFAULT 0, reorder_level INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT,
  UNIQUE(tenant_id, sku));

CREATE TABLE IF NOT EXISTS stock_movements(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, product_id TEXT NOT NULL,
  delta INTEGER NOT NULL, reason TEXT NOT NULL, ref TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_stock ON stock_movements(tenant_id, product_id);

CREATE TABLE IF NOT EXISTS sales(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, receipt_no TEXT NOT NULL,
  total_cents INTEGER NOT NULL DEFAULT 0, payment_method TEXT NOT NULL DEFAULT 'CASH',
  mpesa_ref TEXT, cashier TEXT, created_at TEXT NOT NULL, UNIQUE(tenant_id, receipt_no));
CREATE INDEX IF NOT EXISTS idx_sales_tenant ON sales(tenant_id);

CREATE TABLE IF NOT EXISTS sale_items(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, sale_id TEXT NOT NULL, product_id TEXT NOT NULL,
  qty INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL, line_total_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_saleitems ON sale_items(tenant_id, sale_id);
