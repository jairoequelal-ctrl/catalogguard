from pathlib import Path
import pandas as pd
from src.ingestion import load_catalog, profile_catalog
from src.normalization import build_work_view
from src.matching import match_works
from src.validation import validate_source, validate_reconciliation
from src.reconciliation import build_reconciliation, quality_metrics
from src.reporting import save_sqlite, export_reports

ROOT = Path(__file__).resolve().parent


def run_pipeline():
    internal_catalog = load_catalog(ROOT / "data/raw/internal")
    external_catalog = load_catalog(ROOT / "data/raw/external")

    internal_profile = profile_catalog(internal_catalog).assign(source="internal")
    external_profile = profile_catalog(external_catalog).assign(source="external")
    profiles = pd.concat([internal_profile, external_profile], ignore_index=True)

    internal_view = build_work_view(internal_catalog)
    external_view = build_work_view(external_catalog)
    matches = match_works(internal_view, external_view)

    exceptions = pd.concat([
        validate_source(internal_view, internal_catalog, "internal"),
        validate_source(external_view, external_catalog, "external"),
        validate_reconciliation(matches, internal_view, external_view),
    ], ignore_index=True)
    reconciliation = build_reconciliation(matches, internal_view, external_view)
    metrics = quality_metrics(matches, exceptions, len(internal_view))

    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    internal_view.to_csv(processed / "internal_work_view.csv", index=False)
    external_view.to_csv(processed / "external_work_view.csv", index=False)

    save_sqlite(ROOT / "catalogguard.db", internal_view, external_view, matches, exceptions, reconciliation)
    export_reports(ROOT / "reports", metrics, profiles, matches, exceptions, reconciliation)
    return metrics


if __name__ == "__main__":
    metrics = run_pipeline()
    print("CatalogGuard pipeline completed")
    for key, value in metrics.items():
        print(f"{key}: {value}")
