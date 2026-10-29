-- 0002 billing: subscriptions + usage metering
CREATE TABLE IF NOT EXISTS subscriptions(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, plan_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active', period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT);
CREATE INDEX IF NOT EXISTS idx_sub_tenant ON subscriptions(tenant_id);

CREATE TABLE IF NOT EXISTS usage_events(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, metric TEXT NOT NULL, qty INTEGER NOT NULL,
  month_key TEXT NOT NULL, ref TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_usage ON usage_events(tenant_id, metric, month_key);
