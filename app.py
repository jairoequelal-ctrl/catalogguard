"""Local Streamlit viewer: run reconciliation with the CLI before opening."""
from pathlib import Path
import json
import sqlite3
import pandas as pd
import streamlit as st
from ledgerlens.audit import review

st.set_page_config(page_title='LedgerLens', page_icon='🔎', layout='wide')
st.title('LedgerLens')
st.caption('Payment reconciliation · synthetic portfolio demo · explainable exceptions')
folder = Path(st.sidebar.text_input('Report folder', 'outputs/demo'))
db = folder / 'audit.sqlite'
if not db.exists():
    st.info('First run: python -m ledgerlens demo --output outputs/demo')
    st.stop()
with sqlite3.connect(db) as conn:
    runs = pd.read_sql_query('SELECT run_id, created_at, summary_json FROM runs ORDER BY created_at DESC', conn)
if runs.empty:
    st.info('No runs available.')
    st.stop()
run_id = st.sidebar.selectbox('Audit run', runs.run_id.tolist())
summary = json.loads(runs.loc[runs.run_id == run_id, 'summary_json'].iloc[0])
cols = st.columns(4)
cols[0].metric('Ledger rows', summary['ledger_rows'])
cols[1].metric('Provider rows', summary['provider_rows'])
cols[2].metric('Matched pairs', summary['matched_pairs'])
cols[3].metric('Ledger row match rate', f"{summary['ledger_row_match_rate']:.1%}")
st.caption('Exception findings count rows or pairs, depending on the rule. Amounts are integer cents; currencies are never added together.')
with sqlite3.connect(db) as conn:
    records = conn.execute('SELECT finding_id, evidence_json FROM findings WHERE run_id=? ORDER BY finding_id', (run_id,)).fetchall()
frame = pd.DataFrame([{'finding_id': i, **json.loads(e)} for i, e in records])
if frame.empty:
    st.info('Both sources were empty; there are no findings.')
    st.stop()
statuses = st.multiselect('Statuses', sorted(frame.status.unique()), default=sorted(frame.status.unique()))
filtered = frame[frame.status.isin(statuses)]
st.bar_chart(frame.status.value_counts())
st.dataframe(filtered, use_container_width=True, hide_index=True)
# Re-export through engine protection so user-controlled text cannot become formulas.
from ledgerlens.engine import Finding, write_reports
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    write_reports(tmp, [Finding(**json.loads(e)) for _, e in records], summary)
    st.download_button('Download protected CSV', (Path(tmp) / 'findings.csv').read_bytes(),
                       file_name='findings.csv', mime='text/csv')
st.subheader('Human review')
st.caption('A decision adds an event. It never edits the original finding or moves money.')
exceptions = frame[frame.status != 'MATCHED']
if not exceptions.empty:
    with st.form('review'):
        finding_id = st.selectbox('Finding ID', exceptions.finding_id.tolist())
        reviewer = st.text_input('Reviewer')
        decision = st.selectbox('Decision', ['ACKNOWLEDGED', 'ESCALATED', 'RESOLVED_EXTERNALLY'])
        note = st.text_area('Evidence / explanation')
        submitted = st.form_submit_button('Record review')
    if submitted:
        try:
            event = review(db, run_id, int(finding_id), reviewer, decision, note)
            st.success(f'Review event {event} recorded.')
        except ValueError as exc:
            st.error(str(exc))
with sqlite3.connect(db) as conn:
    history = pd.read_sql_query('SELECT * FROM reviews WHERE run_id=? ORDER BY event_id', conn, params=(run_id,))
st.dataframe(history, use_container_width=True, hide_index=True)
