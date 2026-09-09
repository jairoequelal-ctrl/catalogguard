from pathlib import Path
import pandas as pd

TABLES = ("works", "parties", "ownership", "recordings")


def load_catalog(folder: str | Path) -> dict[str, pd.DataFrame]:
    folder = Path(folder)
    catalog = {}
    for table in TABLES:
        path = folder / f"{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required source file: {path}")
        catalog[table] = pd.read_csv(path, dtype=str).fillna("")
    catalog["ownership"]["ownership_share"] = pd.to_numeric(
        catalog["ownership"]["ownership_share"], errors="coerce"
    )
    return catalog


def profile_catalog(catalog: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table, df in catalog.items():
        rows.append({
            "table": table,
            "rows": len(df),
            "columns": len(df.columns),
            "missing_cells": int(df.eq("").sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
        })
    return pd.DataFrame(rows)
