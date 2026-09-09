import pandas as pd
from src.validation import validate_source


def test_invalid_ownership_total_is_flagged():
    view = pd.DataFrame([{
        "work_id": "I1", "iswc": "T1", "composer_ipis": "123",
        "ownership_total": 90.0, "iswc_norm": "T1"
    }])
    issues = validate_source(view, {}, "internal")
    assert "DQ003" in set(issues["rule_id"])
