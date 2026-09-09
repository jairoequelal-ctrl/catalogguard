CREATE TABLE IF NOT EXISTS audit_exceptions (
    exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field TEXT,
    current_value TEXT,
    external_value TEXT,
    recommended_action TEXT,
    review_status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_rule ON audit_exceptions(rule_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_exceptions(entity_id);
