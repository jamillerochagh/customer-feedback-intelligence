from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from cfi.models import AnalysisConfig, Classification


class Store:
    def __init__(self, path='local/feedback.sqlite'):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS configs (
                    config_id TEXT PRIMARY KEY, config_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS results (
                    review_id TEXT, config_id TEXT, original_text TEXT NOT NULL,
                    status TEXT NOT NULL, result_json TEXT, error TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (review_id, config_id));
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY, review_id TEXT, config_id TEXT,
                    attempt INTEGER, status TEXT, error TEXT, latency_seconds REAL,
                    input_tokens INTEGER, output_tokens INTEGER, actual_model TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY, review_id TEXT, config_id TEXT,
                    result_json TEXT NOT NULL, reviewer TEXT NOT NULL, reason TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, config: AnalysisConfig):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO configs VALUES (?,?)', (config.key, config.model_dump_json()))

    def get(self, rid, config_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM results WHERE review_id=? AND config_id=?', (rid, config_id)).fetchone()
            return dict(row) if row else None

    def attempt(self, rid, cfg, number, status, error, latency, result):
        with self.connect() as db:
            db.execute('''INSERT INTO attempts
                (review_id,config_id,attempt,status,error,latency_seconds,input_tokens,output_tokens,actual_model)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                (rid, cfg, number, status, error, latency,
                 result.input_tokens if result else None,
                 result.output_tokens if result else None,
                 result.actual_model if result else None))

    def save(self, row, cfg, result=None, error=None):
        with self.connect() as db:
            db.execute('''INSERT INTO results (review_id,config_id,original_text,status,result_json,error)
                VALUES (?,?,?,?,?,?) ON CONFLICT(review_id,config_id) DO UPDATE SET
                status=excluded.status,result_json=excluded.result_json,error=excluded.error,
                updated_at=CURRENT_TIMESTAMP''',
                (row['review_id'], cfg, row['text'], 'success' if result else 'failed',
                 result.classification.model_dump_json() if result else None, error))

    def correct(self, rid, cfg, result: Classification, reviewer, reason):
        row = self.get(rid, cfg)
        if not row or row['status'] != 'success':
            raise ValueError('Only successful classifications can be corrected')
        result.grounded(row['original_text'])
        if not reviewer.strip() or not reason.strip():
            raise ValueError('Reviewer and reason are required')
        with self.connect() as db:
            db.execute('INSERT INTO corrections (review_id,config_id,result_json,reviewer,reason) VALUES (?,?,?,?,?)',
                       (rid, cfg, result.model_dump_json(), reviewer, reason))

    def export(self, rows, cfg, include_corrections=True):
        exported = []
        with self.connect() as db:
            for row in rows:
                stored = self.get(row['review_id'], cfg)
                item = dict(row, config_id=cfg, status='pending', reviewed=False)
                if stored:
                    item.update(status=stored['status'], error=stored['error'])
                    if stored['result_json']:
                        item.update(json.loads(stored['result_json']))
                        item['machine_result_json'] = stored['result_json']
                    correction = db.execute('''SELECT * FROM corrections WHERE review_id=? AND config_id=?
                        ORDER BY id DESC LIMIT 1''', (row['review_id'], cfg)).fetchone() if include_corrections else None
                    if correction:
                        item.update(json.loads(correction['result_json']))
                        item.update(reviewed=True, reviewer=correction['reviewer'], correction_reason=correction['reason'])
                exported.append(item)
        return exported

    def audit(self, cfg):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM attempts WHERE config_id=? ORDER BY id', (cfg,))]
