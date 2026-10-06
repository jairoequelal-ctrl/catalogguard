"""One-to-one reconciliation. No fuzzy financial auto-matching."""
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal, InvalidOperation
import csv
import hashlib
import json
from pathlib import Path

REQUIRED = {'record_id', 'reference', 'amount', 'currency', 'posted_at'}

@dataclass(frozen=True)
class Record:
    row: int
    record_id: str
    reference: str
    cents: int | None
    currency: str
    posted_at: date | None
    errors: tuple[str, ...]

@dataclass(frozen=True)
class Finding:
    status: str
    ledger_row: int | None
    provider_row: int | None
    ledger_id: str
    provider_id: str
    reference: str
    ledger_currency: str
    provider_currency: str
    ledger_cents: int | None
    provider_cents: int | None
    delta_cents: int | None
    reason: str


def read_records(path: str | Path) -> list[Record]:
    result = []
    with Path(path).open(newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError('Duplicate CSV column names')
        missing = REQUIRED - set(headers)
        if missing:
            raise ValueError(f'Missing CSV columns: {sorted(missing)}')
        for number, raw in enumerate(reader, 2):
            errors = []
            if None in raw or any(raw.get(k) is None for k in REQUIRED):
                errors.append('malformed CSV row')
            values = {k: (raw.get(k) or '').strip() for k in REQUIRED}
            if not values['record_id']:
                errors.append('missing record_id')
            if not values['reference']:
                errors.append('missing reference')
            # References preserve punctuation and case; only outer whitespace is removed.
            currency = values['currency'].upper()
            if currency not in {'USD', 'EUR', 'GBP'}:
                errors.append('unsupported currency; supported: USD/EUR/GBP')
            cents = None
            try:
                amount = Decimal(values['amount'])
                if not amount.is_finite() or amount * 100 != (amount * 100).to_integral_value():
                    raise ValueError()
                cents = int(amount * 100)
                if abs(cents) > 10**12:
                    raise ValueError()
            except (InvalidOperation, ValueError, OverflowError):
                cents = None
                errors.append('invalid amount: finite, at most two decimals, abs <= 10 billion')
            posted = None
            try:
                posted = date.fromisoformat(values['posted_at'])
            except ValueError:
                errors.append('invalid date: expected ISO YYYY-MM-DD')
            result.append(Record(number, values['record_id'], values['reference'],
                                 cents, currency, posted, tuple(errors)))
    return result


def reconcile(ledger: list[Record], provider: list[Record], max_days: int = 2) -> list[Finding]:
    if not isinstance(max_days, int) or max_days < 0:
        raise ValueError('max_days must be a nonnegative integer')
    findings = []
    used = [set(), set()]
    sources = [ledger, provider]

    def emit(status, left=None, right=None, reason=''):
        # Currency mismatch has no meaningful signed monetary delta.
        delta = (right.cents - left.cents if left and right and
                 left.currency == right.currency and left.cents is not None and
                 right.cents is not None else None)
        findings.append(Finding(status, left.row if left else None,
                                right.row if right else None,
                                left.record_id if left else '', right.record_id if right else '',
                                (left or right).reference, left.currency if left else '',
                                right.currency if right else '', left.cents if left else None,
                                right.cents if right else None, delta, reason))

    # IDs must be unique within each source, including otherwise-invalid rows.
    counts = [Counter(r.record_id for r in rows if r.record_id) for rows in sources]
    blocked_references = set()
    for side, rows in enumerate(sources):
        for index, rec in enumerate(rows):
            errors = list(rec.errors)
            if rec.record_id and counts[side][rec.record_id] > 1:
                errors.append('duplicate record_id within source')
            if errors:
                emit('INVALID_RECORD', rec if side == 0 else None,
                     rec if side == 1 else None, '; '.join(errors))
                used[side].add(index)
                if rec.reference:
                    blocked_references.add(rec.reference)
    groups = [defaultdict(list), defaultdict(list)]
    for side, rows in enumerate(sources):
        for index, rec in enumerate(rows):
            if index not in used[side]:
                groups[side][rec.reference].append(rec)
    for ref in sorted(set(groups[0]) | set(groups[1])):
        left, right = groups[0][ref], groups[1][ref]
        if ref in blocked_references or len(left) > 1 or len(right) > 1:
            for rec in left:
                emit('MANUAL_REVIEW', rec, reason='reference is duplicated or linked to invalid records')
            for rec in right:
                emit('MANUAL_REVIEW', right=rec, reason='reference is duplicated or linked to invalid records')
        elif not left:
            emit('PROVIDER_ONLY', right=right[0], reason='no corresponding ledger reference')
        elif not right:
            emit('LEDGER_ONLY', left[0], reason='no corresponding provider reference')
        else:
            a, b = left[0], right[0]
            issues = []
            if a.currency != b.currency:
                issues.append('currency mismatch')
            if a.cents != b.cents:
                issues.append('amount mismatch')
            if abs((a.posted_at - b.posted_at).days) > max_days:
                issues.append(f'posting date gap exceeds {max_days} days')
            status = ('CURRENCY_MISMATCH' if a.currency != b.currency else
                      'AMOUNT_MISMATCH' if a.cents != b.cents else
                      'DATE_MISMATCH' if issues else 'MATCHED')
            emit(status, a, b, '; '.join(issues) or 'unique reference, exact currency/amount, date within window')
    return findings


def summarize(findings: list[Finding], ledger: list[Record], provider: list[Record]) -> dict:
    counts = dict(sorted(Counter(f.status for f in findings).items()))
    matched = counts.get('MATCHED', 0)
    totals = {}
    for currency in ('USD', 'EUR', 'GBP'):
        a = sum(r.cents for r in ledger if not r.errors and r.currency == currency)
        b = sum(r.cents for r in provider if not r.errors and r.currency == currency)
        totals[currency] = {'ledger_input_cents': a, 'provider_input_cents': b,
                            'provider_minus_ledger_cents': b - a}
    return {'ledger_rows': len(ledger), 'provider_rows': len(provider),
            'matched_pairs': matched, 'exception_findings': len(findings) - matched,
            'ledger_row_match_rate': matched / len(ledger) if ledger else 0,
            'status_counts': counts, 'input_totals_by_currency': totals,
            'totals_note': 'Parse-valid input totals include duplicate IDs/references. Not settled balances.'}


def input_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def report_payload(findings):
    return [asdict(f) for f in findings]


def write_reports(output, findings, summary):
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    # Spreadsheet formula protection applies only to exported text. Stored evidence stays raw.
    def safe(value):
        if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
            return "'" + value
        return value
    with (folder / 'findings.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(Finding.__dataclass_fields__))
        writer.writeheader()
        writer.writerows({k: safe(v) for k, v in asdict(f).items()} for f in findings)
