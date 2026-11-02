"""Private, hash-keyed cache of pure decision-date feature outputs.

Used only by controlled diagnostics. The official path recomputes features.
"""

import json
import sqlite3


def _plain(value):
    if hasattr(value, "item"):
        value = value.item()
    if value is None or type(value) in (bool, int, float, str):
        return value
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _plain(v) for k,v in value.items()}
    raise TypeError("UNSUPPORTED_CACHE_VALUE")


class DiagnosticFeatureCache:
    def __init__(self, path, identity):
        self.connection = sqlite3.connect(path)
        self.pending = 0
        self.connection.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS features (asset INTEGER NOT NULL, day TEXT NOT NULL, holding INTEGER NOT NULL, value TEXT NOT NULL, PRIMARY KEY(asset,day,holding))")
        found = self.connection.execute("SELECT value FROM meta WHERE key='identity'").fetchone()
        if found is None:
            self.connection.execute("INSERT INTO meta VALUES ('identity',?)", (identity,))
            self.connection.commit()
        elif found[0] != identity:
            self.connection.close()
            raise ValueError("DIAGNOSTIC_FEATURE_CACHE_IDENTITY_MISMATCH")

    def get(self, asset, day, holding):
        row = self.connection.execute("SELECT value FROM features WHERE asset=? AND day=? AND holding=?",
                                      (asset, day, int(holding))).fetchone()
        return (False, None) if row is None else (True, json.loads(row[0]))

    def put(self, asset, day, holding, value):
        try:
            payload = json.dumps(_plain(value), allow_nan=False, sort_keys=True)
        except (TypeError, ValueError):
            return
        self.connection.execute("INSERT OR REPLACE INTO features VALUES (?,?,?,?)",
                                (asset, day, int(holding), payload))
        self.pending += 1
        if self.pending >= 1000:
            self.connection.commit()
            self.pending = 0

    def close(self):
        self.connection.commit()
        self.connection.close()
