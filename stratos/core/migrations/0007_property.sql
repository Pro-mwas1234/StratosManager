-- 0007 property rental module
CREATE TABLE IF NOT EXISTS properties(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL, location TEXT,
  created_at TEXT NOT NULL, updated_at TEXT);

CREATE TABLE IF NOT EXISTS units(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, property_id TEXT NOT NULL, label TEXT NOT NULL,
  rent_cents INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'vacant',
  created_at TEXT NOT NULL, updated_at TEXT, UNIQUE(tenant_id, property_id, label));

CREATE TABLE IF NOT EXISTS leases(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, unit_id TEXT NOT NULL, tenant_name TEXT NOT NULL,
  tenant_phone TEXT, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
  rent_cents INTEGER NOT NULL DEFAULT 0, deposit_cents INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL, updated_at TEXT);
CREATE INDEX IF NOT EXISTS idx_leases ON leases(tenant_id, unit_id, status);

CREATE TABLE IF NOT EXISTS rent_bills(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, lease_id TEXT NOT NULL, period TEXT NOT NULL,
  due_date TEXT NOT NULL, amount_cents INTEGER NOT NULL, paid_cents INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, updated_at TEXT,
  UNIQUE(tenant_id, lease_id, period));

CREATE TABLE IF NOT EXISTS rent_payments(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, bill_id TEXT NOT NULL, amount_cents INTEGER NOT NULL,
  method TEXT NOT NULL DEFAULT 'MPESA', reference TEXT, paid_at TEXT, created_at TEXT NOT NULL);
