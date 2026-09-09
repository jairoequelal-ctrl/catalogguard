import re
import unicodedata
import pandas as pd


def normalize_text(value: str) -> str:
    value = "" if value is None else str(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", "" if value is None else str(value)).upper()


def build_work_view(catalog: dict[str, pd.DataFrame]) -> pd.DataFrame:
    works = catalog["works"].copy()
    parties = catalog["parties"].copy()
    ownership = catalog["ownership"].copy()

    joined = ownership.merge(parties, on="party_id", how="left")

    def collect(group: pd.DataFrame, role: str, field: str) -> str:
        values = group.loc[group["role"].eq(role), field]
        return " | ".join(sorted(v for v in values.astype(str) if v))

    grouped = []
    for work_id, group in joined.groupby("work_id"):
        grouped.append({
            "work_id": work_id,
            "composer_names": collect(group, "composer", "name"),
            "composer_ipis": collect(group, "composer", "ipi"),
            "publisher_names": collect(group, "publisher", "name"),
            "publisher_ipis": collect(group, "publisher", "ipi"),
            "ownership_total": float(group["ownership_share"].sum()),
        })
    enriched = works.merge(pd.DataFrame(grouped), on="work_id", how="left")
    for col in ["composer_names", "composer_ipis", "publisher_names", "publisher_ipis"]:
        enriched[col] = enriched[col].fillna("")
    enriched["ownership_total"] = enriched["ownership_total"].fillna(0.0)
    enriched["title_norm"] = enriched["title"].map(normalize_text)
    enriched["composer_norm"] = enriched["composer_names"].map(normalize_text)
    enriched["publisher_norm"] = enriched["publisher_names"].map(normalize_text)
    enriched["iswc_norm"] = enriched["iswc"].map(normalize_identifier)
    enriched["composer_ipis_norm"] = enriched["composer_ipis"].map(normalize_identifier)
    return enriched
