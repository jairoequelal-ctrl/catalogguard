import pandas as pd


def build_reconciliation(matches: pd.DataFrame, internal: pd.DataFrame, external: pd.DataFrame) -> pd.DataFrame:
    i = internal.add_prefix("internal_")
    e = external.add_prefix("external_")
    out = matches.merge(i, left_on="internal_work_id", right_on="internal_work_id", how="left")
    out = out.merge(e, left_on="external_work_id", right_on="external_work_id", how="left")
    return out


def quality_metrics(matches: pd.DataFrame, exceptions: pd.DataFrame, internal_count: int) -> dict:
    total = int(internal_count)
    exact = int(matches["match_method"].eq("EXACT_ISWC").sum())
    review = int(matches["match_status"].eq("MANUAL_REVIEW").sum())
    unmatched = int(matches["match_status"].eq("UNMATCHED").sum())
    external_only = int(matches["match_status"].eq("UNMATCHED_EXTERNAL").sum())
    critical = int(exceptions["severity"].eq("CRITICAL").sum()) if not exceptions.empty else 0
    high = int(exceptions["severity"].eq("HIGH").sum()) if not exceptions.empty else 0
    penalty = min(100, critical * 12 + high * 7 + review * 4 + unmatched * 6 + external_only * 3)
    return {
        "records_processed": total,
        "exact_matches": exact,
        "manual_review": review,
        "unmatched_internal": unmatched,
        "unmatched_external": external_only,
        "exceptions": int(len(exceptions)),
        "critical_exceptions": critical,
        "high_exceptions": high,
        "catalog_quality_score": max(0, 100 - penalty),
    }
