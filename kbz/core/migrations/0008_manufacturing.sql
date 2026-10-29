-- 0008 manufacturing module (BOM + work orders; raw/finished stock uses products & stock_movements)
CREATE TABLE IF NOT EXISTS boms(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, product_id TEXT NOT NULL,
  version TEXT NOT NULL DEFAULT 'v1', active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT, UNIQUE(tenant_id, product_id, version));

CREATE TABLE IF NOT EXISTS bom_components(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, bom_id TEXT NOT NULL, component_product_id TEXT NOT NULL,
  qty REAL NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_bomcomp ON bom_components(tenant_id, bom_id);

CREATE TABLE IF NOT EXISTS work_orders(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, wo_no TEXT NOT NULL, bom_id TEXT NOT NULL,
  qty_planned REAL NOT NULL DEFAULT 1, qty_produced REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'planned', notes TEXT, created_at TEXT NOT NULL, updated_at TEXT,
  UNIQUE(tenant_id, wo_no));
