import pandas as pd
from rapidfuzz.fuzz import ratio


def _text_score(a: pd.Series, b: pd.Series) -> tuple[float, float, float]:
    title = ratio(a["title_norm"], b["title_norm"]) / 100
    composer = ratio(a["composer_norm"], b["composer_norm"]) / 100 if a["composer_norm"] and b["composer_norm"] else 0
    publisher = ratio(a["publisher_norm"], b["publisher_norm"]) / 100 if a["publisher_norm"] and b["publisher_norm"] else 0
    return title, composer, publisher


def match_works(internal: pd.DataFrame, external: pd.DataFrame, review_threshold: float = 0.72) -> pd.DataFrame:
    results = []
    used_external = set()

    for _, left in internal.iterrows():
        candidates = []
        for _, right in external.iterrows():
            exact_iswc = bool(left["iswc_norm"] and left["iswc_norm"] == right["iswc_norm"])
            title_s, composer_s, publisher_s = _text_score(left, right)
            text_score = 0.65 * title_s + 0.30 * composer_s + 0.05 * publisher_s
            candidates.append((exact_iswc, text_score, title_s, composer_s, publisher_s, right))

        identifier_candidates = [c for c in candidates if c[0]]
        pool = identifier_candidates or candidates
        best = max(pool, key=lambda x: x[1])
        exact_iswc, text_score, title_s, composer_s, publisher_s, right = best

        ipi_conflict = bool(
            left["composer_ipis_norm"] and right["composer_ipis_norm"]
            and left["composer_ipis_norm"] != right["composer_ipis_norm"]
        )

        if exact_iswc and not ipi_conflict:
            status = "MATCHED"
            method = "EXACT_ISWC"
            confidence = 1.0
        elif exact_iswc and ipi_conflict:
            status = "MANUAL_REVIEW"
            method = "IDENTIFIER_CONFLICT"
            confidence = 0.95
        elif text_score >= review_threshold:
            status = "MANUAL_REVIEW"
            method = "TEXTUAL_SIMILARITY"
            confidence = round(text_score, 4)
        else:
            status = "UNMATCHED"
            method = "NO_RELIABLE_MATCH"
            confidence = round(text_score, 4)

        external_id = right["work_id"] if status != "UNMATCHED" else ""
        if external_id:
            used_external.add(external_id)

        results.append({
            "internal_work_id": left["work_id"],
            "external_work_id": external_id,
            "match_status": status,
            "match_method": method,
            "match_confidence": confidence,
            "title_similarity": round(title_s, 4),
            "composer_similarity": round(composer_s, 4),
            "publisher_similarity": round(publisher_s, 4),
            "internal_iswc": left["iswc"],
            "external_iswc": right["iswc"] if external_id else "",
        })

    for _, right in external.loc[~external["work_id"].isin(used_external)].iterrows():
        results.append({
            "internal_work_id": "",
            "external_work_id": right["work_id"],
            "match_status": "UNMATCHED_EXTERNAL",
            "match_method": "NO_INTERNAL_RECORD",
            "match_confidence": 0.0,
            "title_similarity": 0.0,
            "composer_similarity": 0.0,
            "publisher_similarity": 0.0,
            "internal_iswc": "",
            "external_iswc": right["iswc"],
        })
    return pd.DataFrame(results)
