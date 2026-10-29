-- 0001 core: tenants, users, tokens
CREATE TABLE IF NOT EXISTS tenants(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, kra_pin TEXT, phone TEXT,
  plan_id TEXT NOT NULL DEFAULT 'starter', status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, tenant_id TEXT, email TEXT NOT NULL UNIQUE,
  pw_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'owner', created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS tokens(
  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'api',
  expires_at TEXT, created_at TEXT NOT NULL);
