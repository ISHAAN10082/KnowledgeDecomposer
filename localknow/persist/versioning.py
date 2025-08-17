import os
import sqlite3
import hashlib
from typing import List, Tuple


SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    mtime REAL NOT NULL,
    size INTEGER NOT NULL,
    content_hash TEXT NOT NULL
);
"""


class VersionTracker:
    def __init__(self, sqlite_path: str):
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        self.conn = sqlite3.connect(sqlite_path)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute(SCHEMA)

    def _hash_bytes(self, b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()

    def record_file(self, path: str, content: str) -> None:
        st = os.stat(path)
        content_hash = self._hash_bytes(content.encode("utf-8", errors="ignore"))
        with self.conn:
            self.conn.execute(
                "REPLACE INTO files(path, mtime, size, content_hash) VALUES(?, ?, ?, ?)",
                (path, st.st_mtime, st.st_size, content_hash),
            )

    def detect_changes(self, paths: List[str], reader) -> Tuple[List[str], List[str]]:
        new_or_modified: List[str] = []
        unchanged: List[str] = []
        for p in paths:
            st = os.stat(p)
            cur = self.conn.execute("SELECT mtime, size, content_hash FROM files WHERE path=?", (p,)).fetchone()
            content = reader(p)
            content_hash = self._hash_bytes(content.encode("utf-8", errors="ignore"))
            if cur is None:
                new_or_modified.append(p)
                continue
            prev_mtime, prev_size, prev_hash = cur
            if abs(prev_mtime - st.st_mtime) > 1e-6 or prev_size != st.st_size or prev_hash != content_hash:
                new_or_modified.append(p)
            else:
                unchanged.append(p)
        return new_or_modified, unchanged 