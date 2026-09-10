from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Any

# ... existing module content ...

    def claim_idempotency(self, key: str, operation: str, fingerprint: str, resource_id: str) -> bool:
        with self._lock, self._connection:
            try:
                self._connection.execute(
                    "INSERT INTO idempotency_keys(key,operation,request_fingerprint,resource_id,created_at) VALUES(?,?,?,?,?)",
                    (key, operation, fingerprint, resource_id, datetime.now().astimezone().isoformat()),
                )
                return True
            except sqlite3.IntegrityError:
                return False
