from datetime import datetime, timezone
import pandas as pd


def _exception(rule_id, severity, entity_id, field, current_value, external_value="", action="Review metadata"):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "entity_type": "WORK",
        "entity_id": entity_id,
        "field": field,
        "current_value": current_value,
        "external_value": external_value,
        "recommended_action": action,
        "review_status": "OPEN",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_source(view: pd.DataFrame, catalog: dict[str, pd.DataFrame], source_name: str) -> pd.DataFrame:
    issues = []
    for _, row in view.iterrows():
        if not row["iswc"]:
            issues.append(_exception("DQ001", "MEDIUM", row["work_id"], "iswc", "", action=f"Verify ISWC in {source_name}"))
        if not row["composer_ipis"]:
            issues.append(_exception("DQ002", "MEDIUM", row["work_id"], "composer_ipi", "", action=f"Verify composer IPI in {source_name}"))
        if abs(float(row["ownership_total"]) - 100.0) > 0.01:
            issues.append(_exception("DQ003", "HIGH", row["work_id"], "ownership_total", row["ownership_total"], action="Review ownership splits; expected total is 100"))

    duplicate_mask = view.duplicated(subset=["iswc_norm"], keep=False) & view["iswc_norm"].ne("")
    for _, row in view.loc[duplicate_mask].iterrows():
        issues.append(_exception("DQ004", "HIGH", row["work_id"], "iswc", row["iswc"], action="Investigate possible duplicate work"))
    return pd.DataFrame(issues)


def validate_reconciliation(matches: pd.DataFrame, internal: pd.DataFrame, external: pd.DataFrame) -> pd.DataFrame:
    issues = []
    i = internal.set_index("work_id")
    e = external.set_index("work_id")

    for _, match in matches.iterrows():
        iid, eid = match["internal_work_id"], match["external_work_id"]
        if match["match_status"] == "UNMATCHED" and iid:
            issues.append(_exception("DQ008", "MEDIUM", iid, "work", iid, action="Investigate work missing from external catalog"))
            continue
        if match["match_status"] == "UNMATCHED_EXTERNAL" and eid:
            issues.append(_exception("DQ009", "MEDIUM", eid, "work", eid, action="Investigate work missing from internal catalog"))
            continue
        if not iid or not eid:
            continue

        left, right = i.loc[iid], e.loc[eid]
        if left["composer_ipis_norm"] and right["composer_ipis_norm"] and left["composer_ipis_norm"] != right["composer_ipis_norm"]:
            issues.append(_exception("DQ006", "CRITICAL", iid, "composer_ipi", left["composer_ipis"], right["composer_ipis"], "Verify party identity before reconciliation"))
        if left["publisher_norm"] and right["publisher_norm"] and left["publisher_norm"] != right["publisher_norm"]:
            issues.append(_exception("DQ005", "HIGH", iid, "publisher", left["publisher_names"], right["publisher_names"], "Review publisher discrepancy"))
        if match["match_method"] == "TEXTUAL_SIMILARITY":
            issues.append(_exception("DQ007", "MEDIUM", iid, "possible_duplicate", left["title"], right["title"], "Send candidate pair to manual review"))
        if left["composer_norm"] != right["composer_norm"] and match["composer_similarity"] >= 0.8:
            issues.append(_exception("DQ010", "LOW", iid, "composer_name", left["composer_names"], right["composer_names"], "Standardize composer name representation"))
    return pd.DataFrame(issues)
