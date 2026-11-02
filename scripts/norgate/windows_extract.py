"""Windows-only, private Norgate source extraction for Batch 4A.

Writes one SQLite file under restricted_norgate/. Never prints observations.
Run with the existing Windows Python and active Norgate Data Updater account.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

import norgatedata as nd


MODES = {
    "NONE": nd.StockPriceAdjustmentType.NONE,
    "CAPITAL": nd.StockPriceAdjustmentType.CAPITAL,
    "CAPITALSPECIAL": nd.StockPriceAdjustmentType.CAPITALSPECIAL,
    "TOTALRETURN": nd.StockPriceAdjustmentType.TOTALRETURN,
}
START = "2025-01-02"
END = "2026-10-30"


def script_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def rows(frame, column):
    if frame is None or frame.empty:
        return []
    return [(index.strftime("%Y-%m-%d"), value) for index, value in frame[column].items()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Private SQLite path under restricted_norgate")
    parser.add_argument("--start", default=START)
    parser.add_argument("--end", default=END)
    parser.add_argument("--symbols", help="Comma-separated small-sample symbols; omit for full watchlist")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if "restricted_norgate" not in output.parts or output.suffix != ".sqlite":
        parser.error("output must be a .sqlite file inside restricted_norgate/")
    if output.exists():
        parser.error("output exists; choose a new versioned filename")
    if args.start > "2025-09-18" or args.end < END:
        parser.error("range must include the full study window and pre-window history")
    output.parent.mkdir(parents=True, exist_ok=True)
    symbols = sorted(set(args.symbols.split(","))) if args.symbols else sorted(set(nd.watchlist_symbols("S&P 500 Current & Past")))
    delisted_symbols = set(nd.database_symbols("US Equities Delisted"))
    if not args.symbols and len(symbols) != 544:
        print(f"NOTICE: watchlist count is {len(symbols)}, not prior observed 544", file=sys.stderr)
    sample = bool(args.symbols)
    if "SPY" not in symbols:
        symbols.append("SPY")
    # SQLite file locking is unreliable on the WSL UNC share. Build on the
    # Windows local temporary volume, then copy the closed database once.
    with tempfile.TemporaryDirectory(prefix="norgate_batch4a_") as local_dir:
      local_db = Path(local_dir) / "extract.sqlite"
      conn = sqlite3.connect(local_db)
      try:
        conn.executescript("""
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE securities (asset_id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, status TEXT, is_candidate INTEGER NOT NULL);
        CREATE TABLE prices (asset_id INTEGER NOT NULL, mode TEXT NOT NULL, date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL, turnover REAL,
            unadjusted_close REAL, dividend REAL, PRIMARY KEY(asset_id,mode,date));
        CREATE TABLE membership (asset_id INTEGER NOT NULL, date TEXT NOT NULL, eligible INTEGER NOT NULL,
            PRIMARY KEY(asset_id,date));
        CREATE TABLE capital_events (asset_id INTEGER NOT NULL, date TEXT NOT NULL, flag INTEGER NOT NULL,
            PRIMARY KEY(asset_id,date));
        CREATE TABLE errors (symbol TEXT NOT NULL, stage TEXT NOT NULL, message TEXT NOT NULL);
        """)
        metadata = {
            "source": "Norgate Data US Stocks Platinum trial",
            "watchlist": "S&P 500 Current & Past",
            "index": "S&P 500",
            "acquired_utc": datetime.now(timezone.utc).isoformat(),
            "start": args.start, "end": args.end,
            "modes": ",".join(MODES), "padding": "NONE",
            "python": sys.version.split()[0],
            "norgatedata": importlib.metadata.version("norgatedata"),
            "extractor_sha256": script_hash(),
            "sample": str(sample).lower(),
            "candidate_count": str(len(symbols) - 1 if "SPY" in symbols else len(symbols)),
            "ndu_version": "NOT_AVAILABLE_FROM_PYTHON; see manually recorded 4.2.2.65",
        }
        conn.executemany("INSERT INTO metadata VALUES (?,?)", metadata.items())
        for number, symbol in enumerate(symbols, 1):
            try:
                asset_id = int(nd.assetid(symbol))
                status = "DELISTED_DATABASE" if symbol in delisted_symbols else "OTHER"
                conn.execute("INSERT INTO securities VALUES (?,?,?,?)", (asset_id, symbol, status, int(symbol != "SPY")))
            except Exception as exc:
                conn.execute("INSERT INTO errors VALUES (?,?,?)", (symbol, "identity", str(exc)[:300]))
                continue
            for mode_name, mode in MODES.items():
                try:
                    frame = nd.price_timeseries(asset_id, stock_price_adjustment_setting=mode,
                        padding_setting=nd.PaddingType.NONE, start_date=args.start, end_date=args.end,
                        timeseriesformat="pandas-dataframe")
                    if frame is None or frame.empty:
                        continue
                    records = []
                    for date, row in frame.iterrows():
                        records.append((asset_id, mode_name, date.strftime("%Y-%m-%d"),
                            *(float(row.get(key)) if row.get(key) is not None else None
                              for key in ("Open", "High", "Low", "Close", "Volume", "Turnover", "Unadjusted Close", "Dividend"))))
                    conn.executemany("INSERT INTO prices VALUES (?,?,?,?,?,?,?,?,?,?,?)", records)
                except Exception as exc:
                    conn.execute("INSERT INTO errors VALUES (?,?,?)", (symbol, "price_" + mode_name, str(exc)[:300]))
            if symbol != "SPY":
                for stage, method, column, table in (
                    ("membership", nd.index_constituent_timeseries, "Index Constituent", "membership"),
                    ("capital", nd.capital_event_timeseries, "Capital Event", "capital_events"),
                ):
                    try:
                        kw = dict(padding_setting=nd.PaddingType.NONE, start_date=args.start,
                                  end_date=args.end, timeseriesformat="pandas-dataframe")
                        frame = method(asset_id, "S&P 500", **kw) if stage == "membership" else method(asset_id, **kw)
                        values = [(asset_id, date, int(value)) for date, value in rows(frame, column)
                                  if args.start <= date <= args.end and value == value]
                        conn.executemany(f"INSERT INTO {table} VALUES (?,?,?)", values)
                    except Exception as exc:
                        conn.execute("INSERT INTO errors VALUES (?,?,?)", (symbol, stage, str(exc)[:300]))
            conn.commit()
            if number % 25 == 0 or number == len(symbols):
                print(f"Processed {number}/{len(symbols)} securities; no source rows printed", flush=True)
        conn.execute("INSERT INTO metadata VALUES (?,?)", ("complete", "true"))
        conn.commit()
      finally:
          conn.close()
      if output.exists():
          parser.error("output appeared during extraction; refusing overwrite")
      shutil.copyfile(local_db, output)
    print(f"Extraction complete; private file: {output.name}")


if __name__ == "__main__":
    main()
