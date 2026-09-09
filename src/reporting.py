from pathlib import Path
import sqlite3
import pandas as pd


def save_sqlite(db_path: str | Path, internal_view: pd.DataFrame, external_view: pd.DataFrame, matches: pd.DataFrame, exceptions: pd.DataFrame, reconciliation: pd.DataFrame):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        internal_view.to_sql("internal_work_view", conn, if_exists="replace", index=False)
        external_view.to_sql("external_work_view", conn, if_exists="replace", index=False)
        matches.to_sql("matches", conn, if_exists="replace", index=False)
        exceptions.to_sql("exceptions", conn, if_exists="replace", index=False)
        reconciliation.to_sql("reconciliation", conn, if_exists="replace", index=False)


def export_reports(report_dir: str | Path, metrics: dict, profiles: pd.DataFrame, matches: pd.DataFrame, exceptions: pd.DataFrame, reconciliation: pd.DataFrame):
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([metrics]).to_csv(report_dir / "quality_summary.csv", index=False)
    matches.to_csv(report_dir / "matches.csv", index=False)
    exceptions.to_csv(report_dir / "exceptions.csv", index=False)
    reconciliation.to_csv(report_dir / "reconciliation.csv", index=False)
    with pd.ExcelWriter(report_dir / "catalogguard_report.xlsx", engine="openpyxl") as writer:
        pd.DataFrame([metrics]).to_excel(writer, sheet_name="Summary", index=False)
        profiles.to_excel(writer, sheet_name="Profiling", index=False)
        matches.to_excel(writer, sheet_name="Matches", index=False)
        exceptions.to_excel(writer, sheet_name="Exceptions", index=False)
        reconciliation.to_excel(writer, sheet_name="Reconciliation", index=False)
