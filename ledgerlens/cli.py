import argparse
import json
from pathlib import Path
from . import __version__
from .audit import save_run, review
from .demo import generate
from .engine import read_records, reconcile, summarize, write_reports, input_hash


def run(ledger_path, provider_path, output, max_days=2):
    ledger, provider = read_records(ledger_path), read_records(provider_path)
    findings = reconcile(ledger, provider, max_days)
    summary = summarize(findings, ledger, provider)
    config = {'max_days': max_days, 'engine_version': __version__}
    run_id = save_run(Path(output) / 'audit.sqlite', input_hash(ledger_path),
                      input_hash(provider_path), config, findings, summary)
    summary['run_id'] = run_id
    write_reports(output, findings, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description='LedgerLens payment reconciliation')
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='Generate synthetic sources and reconcile them')
    demo.add_argument('--output', default='outputs/demo')
    rec = sub.add_parser('reconcile', help='Reconcile two CSV sources')
    rec.add_argument('--ledger', required=True)
    rec.add_argument('--provider', required=True)
    rec.add_argument('--output', default='outputs/run')
    rec.add_argument('--max-days', type=int, default=2)
    rev = sub.add_parser('review', help='Append a human decision; never modifies source evidence')
    rev.add_argument('--db', required=True)
    rev.add_argument('--run-id', required=True)
    rev.add_argument('--finding-id', required=True, type=int)
    rev.add_argument('--reviewer', required=True)
    rev.add_argument('--decision', choices=['ACKNOWLEDGED', 'ESCALATED', 'RESOLVED_EXTERNALLY'], required=True)
    rev.add_argument('--note', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'demo':
            a, b = generate(Path(args.output) / 'inputs')
            result = run(a, b, args.output)
        elif args.command == 'reconcile':
            result = run(args.ledger, args.provider, args.output, args.max_days)
        else:
            result = {'review_event_id': review(args.db, args.run_id, args.finding_id,
                                               args.reviewer, args.decision, args.note)}
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')

if __name__ == '__main__':
    main()
