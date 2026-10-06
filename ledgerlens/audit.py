"""Append-only application audit: reproducible runs and immutable review events."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .engine import report_payload

SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
 run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
 ledger_sha256 TEXT NOT NULL, provider_sha256 TEXT NOT NULL,
 config_json TEXT NOT NULL, summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
 run_id TEXT NOT NULL REFERENCES runs(run_id), finding_id INTEGER NOT NULL,
 status TEXT NOT NULL, evidence_json TEXT NOT NULL,
 PRIMARY KEY(run_id, finding_id)
);
CREATE TABLE IF NOT EXISTS reviews (
 event_id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, finding_id INTEGER NOT NULL,
 created_at TEXT NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL, note TEXT NOT NULL,
 FOREIGN KEY(run_id, finding_id) REFERENCES findings(run_id, finding_id)
);
'''


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def save_run(path, ledger_hash, provider_hash, config, findings, summary):
    canonical = json.dumps({'ledger': ledger_hash, 'provider': provider_hash, 'config': config}, sort_keys=True)
    run_id = hashlib.sha256(canonical.encode()).hexdigest()
    conn = connect(path)
    try:
        with conn:
            exists = conn.execute('SELECT 1 FROM runs WHERE run_id=?', (run_id,)).fetchone()
            if not exists:
                conn.execute('INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)',
                             (run_id, datetime.now(timezone.utc).isoformat(), ledger_hash,
                              provider_hash, json.dumps(config, sort_keys=True), json.dumps(summary)))
                conn.executemany('INSERT INTO findings VALUES (?, ?, ?, ?)',
                                 [(run_id, i, f['status'], json.dumps(f))
                                  for i, f in enumerate(report_payload(findings), 1)])
    finally:
        conn.close()
    return run_id


def review(path, run_id, finding_id, reviewer, decision, note):
    if decision not in {'ACKNOWLEDGED', 'ESCALATED', 'RESOLVED_EXTERNALLY'}:
        raise ValueError('Invalid review decision')
    if not reviewer.strip() or not note.strip():
        raise ValueError('Reviewer and evidence note are required')
    conn = connect(path)
    try:
        with conn:
            item = conn.execute('SELECT status FROM findings WHERE run_id=? AND finding_id=?',
                                (run_id, finding_id)).fetchone()
            if item is None or item[0] == 'MATCHED':
                raise ValueError('Choose an existing exception finding')
            cursor = conn.execute('INSERT INTO reviews VALUES (NULL, ?, ?, ?, ?, ?, ?)',
                                  (run_id, finding_id, datetime.now(timezone.utc).isoformat(),
                                   reviewer.strip(), decision, note.strip()))
            return cursor.lastrowid
    finally:
        conn.close()
