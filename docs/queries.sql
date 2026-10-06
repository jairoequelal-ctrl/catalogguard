-- SQLite CLI: sqlite3 outputs/demo/audit.sqlite
-- Latest run, then choose one run ID for detailed investigation.
SELECT run_id, created_at, summary_json FROM runs ORDER BY created_at DESC;

-- Status distribution by run (never mix historical runs into one match rate).
SELECT run_id, status, COUNT(*) AS findings
FROM findings GROUP BY run_id, status ORDER BY run_id, status;

-- Explain amount discrepancies, keeping currency attached to every delta.
SELECT run_id, finding_id,
       json_extract(evidence_json, '$.reference') AS reference,
       json_extract(evidence_json, '$.ledger_currency') AS currency,
       json_extract(evidence_json, '$.delta_cents') AS provider_minus_ledger_cents,
       json_extract(evidence_json, '$.reason') AS reason
FROM findings WHERE status = 'AMOUNT_MISMATCH';

-- Exceptions without review; filter a specific run in a real investigation.
SELECT f.run_id, f.finding_id, f.status, f.evidence_json
FROM findings f
WHERE f.status <> 'MATCHED'
AND NOT EXISTS (
 SELECT 1 FROM reviews r WHERE r.run_id = f.run_id AND r.finding_id = f.finding_id
);

-- Latest operator decision, with original engine status preserved.
SELECT f.run_id, f.finding_id, f.status AS original_status,
       r.decision, r.reviewer, r.note, r.created_at
FROM findings f
LEFT JOIN reviews r ON r.event_id = (
 SELECT MAX(r2.event_id) FROM reviews r2
 WHERE r2.run_id = f.run_id AND r2.finding_id = f.finding_id
)
WHERE f.status <> 'MATCHED';
