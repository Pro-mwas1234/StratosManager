-- 0003 invoicing module
CREATE TABLE IF NOT EXISTS customers(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL, email TEXT, phone TEXT,
  kra_pin TEXT, address TEXT, created_at TEXT NOT NULL, updated_at TEXT);
CREATE INDEX IF NOT EXISTS idx_cust_tenant ON customers(tenant_id);

CREATE TABLE IF NOT EXISTS invoices(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, number TEXT NOT NULL, customer_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft', issue_date TEXT, due_date TEXT, currency TEXT DEFAULT 'KES',
  net_cents INTEGER NOT NULL DEFAULT 0, vat_cents INTEGER NOT NULL DEFAULT 0,
  gross_cents INTEGER NOT NULL DEFAULT 0, paid_cents INTEGER NOT NULL DEFAULT 0,
  notes TEXT, mpesa_ref TEXT, created_at TEXT NOT NULL, updated_at TEXT,
  UNIQUE(tenant_id, number));

CREATE TABLE IF NOT EXISTS invoice_lines(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, invoice_id TEXT NOT NULL, description TEXT NOT NULL,
  qty REAL NOT NULL DEFAULT 1, unit_price_cents INTEGER NOT NULL DEFAULT 0,
  vat_rate REAL NOT NULL DEFAULT 0.16, line_net_cents INTEGER NOT NULL DEFAULT 0,
  line_vat_cents INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_invline ON invoice_lines(tenant_id, invoice_id);

CREATE TABLE IF NOT EXISTS payments(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, invoice_id TEXT NOT NULL,
  method TEXT NOT NULL DEFAULT 'MPESA', reference TEXT, amount_cents INTEGER NOT NULL,
  paid_at TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_pay ON payments(tenant_id, invoice_id);
