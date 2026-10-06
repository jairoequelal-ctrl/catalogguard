import csv
import json
import sqlite3
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from ledgerlens.engine import read_records, reconcile, summarize, write_reports
from ledgerlens.demo import generate, EXPECTED, HEADER
from ledgerlens.audit import save_run, review
from ledgerlens.cli import run

class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def rows(self, rows, name='input.csv'):
        path = self.root / name
        with path.open('w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(HEADER)
            writer.writerows(rows)
        return read_records(path)

    def record(self, ident='A', ref='PAY', amount='0.30', currency='USD', day='2026-01-01'):
        return [ident, ref, amount, currency, day]

    def test_demo_ground_truth_and_row_conservation(self):
        a, b = generate(self.root)
        left, right = read_records(a), read_records(b)
        findings = reconcile(left, right)
        self.assertEqual(dict(Counter(f.status for f in findings)), EXPECTED)
        self.assertEqual(Counter(f.ledger_row for f in findings if f.ledger_row),
                         Counter(r.row for r in left))
        self.assertEqual(Counter(f.provider_row for f in findings if f.provider_row),
                         Counter(r.row for r in right))

    def test_decimal_precision_and_negative_refunds(self):
        for amount in ['0.30', '-25.50', '0.00', '100000.01']:
            a = self.rows([self.record(amount=amount)])
            self.assertEqual(reconcile(a, a)[0].status, 'MATCHED')
        self.assertEqual(self.rows([self.record()])[0].cents, 30)

    def test_invalid_values_are_quarantined(self):
        for amount in ['NaN', 'Infinity', '1.001', 'oops', '10000000001']:
            a = self.rows([self.record(amount=amount)])
            b = self.rows([self.record(ident='B')], 'provider.csv')
            self.assertEqual([f.status for f in reconcile(a, b)],
                             ['INVALID_RECORD', 'MANUAL_REVIEW'])

    def test_duplicate_ids_block_otherwise_valid_references(self):
        a = self.rows([self.record(), self.record(ref='OTHER')])
        b = self.rows([self.record(ident='B')], 'provider.csv')
        counts = Counter(f.status for f in reconcile(a, b))
        self.assertEqual(counts, {'INVALID_RECORD': 2, 'MANUAL_REVIEW': 1})

    def test_duplicate_reference_never_arbitrarily_matches(self):
        a = self.rows([self.record(), self.record(ident='B')])
        b = self.rows([self.record(ident='C')], 'provider.csv')
        self.assertEqual(Counter(f.status for f in reconcile(a, b)), {'MANUAL_REVIEW': 3})

    def test_currency_mismatch_does_not_compute_fx_delta(self):
        a = self.rows([self.record()])
        b = self.rows([self.record(currency='EUR')], 'provider.csv')
        f = reconcile(a, b)[0]
        self.assertEqual(f.status, 'CURRENCY_MISMATCH')
        self.assertIsNone(f.delta_cents)

    def test_date_boundary_is_inclusive(self):
        a = self.rows([self.record()])
        for day, expected in [('2026-01-03', 'MATCHED'), ('2026-01-04', 'DATE_MISMATCH')]:
            b = self.rows([self.record(day=day)], 'provider.csv')
            self.assertEqual(reconcile(a, b)[0].status, expected)
        with self.assertRaises(ValueError):
            reconcile(a, a, -1)

    def test_empty_and_malformed_inputs(self):
        self.assertEqual(summarize([], [], [])['ledger_row_match_rate'], 0)
        p = self.root / 'bad.csv'
        p.write_text('id,amount\nA,1\n')
        with self.assertRaises(ValueError):
            read_records(p)
        self.assertTrue(self.rows([self.record(day='2026-02-30')])[0].errors)
        self.assertTrue(self.rows([self.record(currency='JPY')])[0].errors)

    def test_all_mismatch_reasons_preserved(self):
        a = self.rows([self.record()])
        b = self.rows([self.record(amount='3.00', currency='EUR', day='2026-02-01')], 'provider.csv')
        self.assertEqual(len(reconcile(a, b)[0].reason.split('; ')), 3)

    def test_csv_formula_protection(self):
        a = self.rows([self.record(ref='=1+1')])
        findings = reconcile(a, [])
        write_reports(self.root, findings, summarize(findings, a, []))
        with (self.root / 'findings.csv').open() as file:
            row = next(csv.DictReader(file))
        self.assertEqual(row['reference'], "'=1+1")
        self.assertEqual(findings[0].reference, '=1+1')

    def test_idempotency_and_review_history(self):
        a, b = generate(self.root)
        first = run(a, b, self.root / 'output')
        second = run(a, b, self.root / 'output')
        self.assertEqual(first, second)
        db = self.root / 'output' / 'audit.sqlite'
        for decision in ['ESCALATED', 'RESOLVED_EXTERNALLY']:
            review(db, first['run_id'], 1, 'test-reviewer', decision, 'Synthetic evidence')
        with sqlite3.connect(db) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0], 2)
            matched = conn.execute("SELECT finding_id FROM findings WHERE status='MATCHED' LIMIT 1").fetchone()[0]
        with self.assertRaises(ValueError):
            review(db, first['run_id'], matched, 'reviewer', 'ACKNOWLEDGED', 'note')
        changed = run(a, b, self.root / 'output', max_days=0)
        self.assertNotEqual(first['run_id'], changed['run_id'])

if __name__ == '__main__':
    unittest.main()
