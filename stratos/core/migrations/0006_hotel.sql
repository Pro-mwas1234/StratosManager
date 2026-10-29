-- 0006 hotel module
CREATE TABLE IF NOT EXISTS rooms(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, number TEXT NOT NULL, room_type TEXT DEFAULT 'standard',
  rate_cents INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'available',
  created_at TEXT NOT NULL, updated_at TEXT, UNIQUE(tenant_id, number));

CREATE TABLE IF NOT EXISTS bookings(
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, guest_name TEXT NOT NULL, guest_phone TEXT,
  room_id TEXT NOT NULL, check_in_date TEXT NOT NULL, check_out_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'reserved', nights INTEGER NOT NULL DEFAULT 1,
  total_cents INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT);
CREATE INDEX IF NOT EXISTS idx_bookings ON bookings(tenant_id, room_id, check_in_date, check_out_date);
