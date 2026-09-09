import pandas as pd
from src.matching import match_works


def row(work_id, title, iswc, composer, ipis):
    return {
        "work_id": work_id,
        "title": title,
        "iswc": iswc,
        "title_norm": title.lower(),
        "composer_norm": composer.lower(),
        "publisher_norm": "",
        "composer_ipis_norm": ipis,
    }


def test_matching_sends_identifier_conflict_to_review():
    internal = pd.DataFrame([row("I1", "Song", "T1", "Maria", "111")])
    external = pd.DataFrame([row("E1", "Song", "T1", "Maria", "222")])
    result = match_works(internal, external)
    assert result.iloc[0]["match_status"] == "MANUAL_REVIEW"
    assert result.iloc[0]["match_method"] == "IDENTIFIER_CONFLICT"
