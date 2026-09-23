import json, os, sqlite3, threading, time


class Cache:
    """Thread-safe SQLite enrichment cache.

    The database directory is created automatically so LeadForge can be
    launched from any working directory (including a desktop shortcut).
    """

    def __init__(self, path="cache/enrichment_cache.db", ttl_days=30):
        self.path = os.path.abspath(os.path.expanduser(path))
        self.ttl = ttl_days * 86400
        self.lock = threading.RLock()
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        # Ensure SQLite is never asked to create a DB inside a missing folder.
        self.conn = sqlite3.connect(
            self.path, check_same_thread=False, timeout=30
        )
        with self.conn:
            self.conn.execute("PRAGMA busy_timeout=30000")
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                "k TEXT PRIMARY KEY, value TEXT NOT NULL, ts REAL NOT NULL)"
            )

    def key(self, name, address):
        return (name or "").strip().lower() + "\n" + (address or "").strip().lower()

    def get(self, name, address):
        k = self.key(name, address)
        with self.lock:
            row = self.conn.execute(
                "SELECT value,ts FROM cache WHERE k=?", (k,)
            ).fetchone()
        if not row:
            return None
        if time.time() - row[1] > self.ttl:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def set(self, name, address, value):
        k = self.key(name, address)
        payload = json.dumps(value, ensure_ascii=False)
        with self.lock:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO cache(k,value,ts) VALUES(?,?,?)",
                    (k, payload, time.time()),
                )

    def close(self):
        with self.lock:
            try:
                self.conn.close()
            except Exception:
                pass
