import time
import concurrent.futures
from unittest.mock import MagicMock

# Simulated network latency in seconds
LATENCY = 0.05

def mock_fetch(data):
    time.sleep(LATENCY)
    return MagicMock(data=data)

def load_users_original(db, rbac_data, legacy_data):
    _user_roles = {}
    _approved_users = set()

    start_time = time.perf_counter()

    # 1. Sequential fetch and loop
    rows = db.table("aisha_users").select("telegram_user_id, role").execute(rbac_data).data or []
    for row in rows:
        uid = row["telegram_user_id"]
        role = row["role"]
        _user_roles[uid] = role
        _approved_users.add(uid)

    legacy_rows = db.table("aisha_approved_users").select("telegram_user_id").eq("is_active", True).execute(legacy_data).data or []
    for row in legacy_rows:
        uid = row["telegram_user_id"]
        if uid not in _user_roles:
            _user_roles[uid] = "guest"
            _approved_users.add(uid)

    end_time = time.perf_counter()
    return end_time - start_time

def load_users_optimized(db, rbac_data, legacy_data):
    _user_roles = {}
    _approved_users = set()

    start_time = time.perf_counter()

    # 1. Parallel fetch
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(lambda: db.table("aisha_users").select("telegram_user_id, role").execute(rbac_data).data or [])
        f2 = executor.submit(lambda: db.table("aisha_approved_users").select("telegram_user_id").eq("is_active", True).execute(legacy_data).data or [])

        rbac_rows = f1.result()
        legacy_rows = f2.result()

    # 2. Bulk updates
    # Precedence: legacy first, then rbac (RBAC roles override legacy 'guest' roles if same UID exists)
    # However, the original logic only adds legacy if NOT in rbac.
    # So we do RBAC first, then add ONLY missing legacy.

    _user_roles = {row["telegram_user_id"]: row["role"] for row in rbac_rows}
    _approved_users = set(_user_roles.keys())

    legacy_uids = {row["telegram_user_id"] for row in legacy_rows}
    new_legacy_uids = legacy_uids - _approved_users

    _user_roles.update({uid: "guest" for uid in new_legacy_uids})
    _approved_users.update(new_legacy_uids)

    end_time = time.perf_counter()
    return end_time - start_time

class MockDB:
    def table(self, name):
        self.current_table = name
        return self
    def select(self, query):
        return self
    def eq(self, col, val):
        return self
    def execute(self, data):
        return mock_fetch(data)

if __name__ == "__main__":
    n = 5000
    rbac_data = [{"telegram_user_id": i, "role": "guest"} for i in range(n)]
    legacy_data = [{"telegram_user_id": i} for i in range(n//2, n + n//2)]

    db = MockDB()

    print(f"Benchmarking with {n} users per table and {LATENCY}s simulated latency...")

    # Warmup
    load_users_original(db, rbac_data, legacy_data)
    load_users_optimized(db, rbac_data, legacy_data)

    t1 = load_users_original(db, rbac_data, legacy_data)
    print(f"Original:  {t1:.4f}s")

    t2 = load_users_optimized(db, rbac_data, legacy_data)
    print(f"Optimized: {t2:.4f}s")

    print(f"Speedup: {t1/t2:.2f}x ({(t1-t2)/t1*100:.1f}% faster)")
