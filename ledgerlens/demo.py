"""Deterministic synthetic fixtures with independently declared expected outcomes."""
import csv
import json
from pathlib import Path

HEADER = ['record_id', 'reference', 'amount', 'currency', 'posted_at']
EXPECTED = {'MATCHED': 3, 'AMOUNT_MISMATCH': 1, 'CURRENCY_MISMATCH': 1,
            'DATE_MISMATCH': 1, 'LEDGER_ONLY': 1, 'PROVIDER_ONLY': 1,
            'MANUAL_REVIEW': 4, 'INVALID_RECORD': 3}


def generate(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    ledger = [
        ['L01', 'PAY-001', '100.00', 'USD', '2026-01-01'],
        ['L02', 'PAY-002', '0.30', 'USD', '2026-01-01'],
        ['L03', 'REFUND-003', '-25.50', 'USD', '2026-01-01'],
        ['L04', 'PAY-004', '50.00', 'USD', '2026-01-01'],
        ['L05', 'PAY-005', '75.00', 'USD', '2026-01-01'],
        ['L06', 'PAY-006', '90.00', 'EUR', '2026-01-01'],
        ['L07', 'PAY-007', '20.00', 'USD', '2026-01-01'],
        ['L08', 'PAY-008', '12.00', 'USD', '2026-01-01'],
        ['L09', 'PAY-008', '12.00', 'USD', '2026-01-01'],
        ['L10', 'PAY-010', 'NaN', 'USD', '2026-01-01'],
        ['DUP', 'PAY-011', '15.00', 'USD', '2026-01-01'],
        ['DUP', 'PAY-012', '16.00', 'USD', '2026-01-01'],
    ]
    provider = [
        ['P01', 'PAY-001', '100.00', 'USD', '2026-01-02'],
        ['P02', 'PAY-002', '0.30', 'USD', '2026-01-01'],
        ['P03', 'REFUND-003', '-25.50', 'USD', '2026-01-03'],
        ['P04', 'PAY-004', '48.00', 'USD', '2026-01-01'],
        ['P05', 'PAY-005', '75.00', 'USD', '2026-01-08'],
        ['P06', 'PAY-006', '90.00', 'USD', '2026-01-01'],
        ['P08', 'PAY-008', '12.00', 'USD', '2026-01-01'],
        ['P09', 'PAY-009', '30.00', 'USD', '2026-01-01'],
        ['P10', 'PAY-010', '8.00', 'USD', '2026-01-01'],
    ]
    for name, rows in [('ledger.csv', ledger), ('provider.csv', provider)]:
        with (folder / name).open('w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(HEADER)
            writer.writerows(rows)
    (folder / 'expected.json').write_text(json.dumps(EXPECTED, indent=2) + '\n')
    return folder / 'ledger.csv', folder / 'provider.csv'
