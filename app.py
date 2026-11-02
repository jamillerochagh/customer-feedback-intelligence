from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from cfi.ingest import map_rows, read_csv
from cfi.models import AnalysisConfig, Classification, SENTIMENTS, THEMES
from cfi.pipeline import analyze
from cfi.providers import Baseline, OpenAIProvider
from cfi.reporting import json_export, priorities, safe_csv
from cfi.store import Store

ROOT = Path(__file__).parent
load_dotenv(ROOT / '.env')
st.set_page_config(page_title='Customer Feedback Intelligence', page_icon='💬', layout='wide')
st.title('Customer Feedback Intelligence')
st.caption('From customer reviews to traceable classifications and investigation priorities.')

with st.sidebar:
    st.header('Analysis settings')
    mode = st.selectbox('Engine', ['Keyword baseline · local demo', 'OpenAI · real LLM'], key='engine')
    is_llm = mode.startswith('OpenAI')
    model = st.text_input('Model snapshot', os.getenv('OPENAI_MODEL', 'gpt-4.1-mini-2025-04-14'), disabled=not is_llm)
    limit = st.number_input('Maximum reviews per click', min_value=1, max_value=100, value=30)
    st.caption('Successful results are reused for identical text and configuration. Failed rows can be retried.')
    if is_llm:
        st.info('Review text is sent to OpenAI only when you click Analyze. Use data you are allowed to send.')
    else:
        st.warning('LOCAL BASELINE — simple English keywords. No LLM calls. All outputs require review.')

config = AnalysisConfig(provider='openai' if is_llm else 'baseline', model=model if is_llm else 'keyword-v1')
store = Store(os.getenv('CFI_DB', str(ROOT / 'local/feedback.sqlite')))
store.register(config)

st.subheader('1. Load and map')
source = st.radio('Data source', ['Public sample (UCI restaurant reviews)', 'Upload CSV'], horizontal=True)
if source.startswith('Public'):
    path = ROOT / 'data/demo.csv'
    if not path.exists():
        st.error('Sample missing. Run: python -m scripts.prepare_data')
        st.stop()
    raw = path.read_bytes()
    st.caption('30 restaurant review sentences. UCI / Kotzias (2015), CC BY 4.0. No dates or ratings supplied.')
    st.markdown('[Dataset and license](https://archive.ics.uci.edu/dataset/331/sentiment+labelled+sentences)')
else:
    upload = st.file_uploader('UTF-8 CSV · up to 5 MB / 5,000 rows', type=['csv'])
    if not upload:
        st.stop()
    raw = upload.getvalue()
try:
    frame = read_csv(raw)
    cols = list(frame.columns)
    a, b, c = st.columns(3)
    text_col = a.selectbox('Review text column', cols, index=cols.index('text') if 'text' in cols else 0)
    date_col = b.selectbox('Date column (optional; ISO dates recommended)', [None] + cols)
    rating_col = c.selectbox('Rating column (optional; preserved as supplied)', [None] + cols)
    rows, rejected = map_rows(frame, text_col, date_col, rating_col)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
st.dataframe(frame.head(5), hide_index=True, width='stretch')
st.caption(f'{len(rows)} unique valid reviews · {len(rejected)} excluded rows. Exact duplicate texts count once.')
if rejected:
    with st.expander('Excluded rows and reasons'):
        st.dataframe(rejected, hide_index=True)
        st.download_button('Download ingestion report', safe_csv(rejected), 'ingestion_report.csv', 'text/csv')
if not rows:
    st.stop()

st.subheader('2. Analyze')
selected = rows[:int(limit)]
st.caption(f'This click considers the first {len(selected)} reviews. Increase the limit to include more. Cached successes consume no API calls.')
key = os.getenv('OPENAI_API_KEY', '')
if is_llm and not key:
    st.warning('Set OPENAI_API_KEY in .env to enable real LLM analysis. The local baseline works without a key.')
if st.button('Analyze', type='primary', disabled=is_llm and not key):
    provider = OpenAIProvider(key, config) if is_llm else Baseline()
    bar = st.progress(0.0)
    try:
        counts = analyze(selected, config, provider, store, bar.progress)
        st.success(f"New successes: {counts['success']} · cached: {counts['cached']} · failed: {counts['failed']}")
    finally:
        if is_llm:
            provider.close()

results = store.export(rows, config.key)
table = pd.DataFrame(results)
st.subheader('3. Explore evidence')
a, b, c = st.columns(3)
a.metric('Successful', sum(r['status'] == 'success' for r in results))
b.metric('Pending', sum(r['status'] == 'pending' for r in results))
c.metric('Failed', sum(r['status'] == 'failed' for r in results))
successful = table[table.status == 'success'].copy()
if not successful.empty:
    a, b, c = st.columns(3)
    themes = a.multiselect('Theme', THEMES)
    sentiments = b.multiselect('Sentiment', SENTIMENTS)
    review_only = c.checkbox('Needs review only')
    filtered = successful
    if themes:
        filtered = filtered[filtered.theme.isin(themes)]
    if sentiments:
        filtered = filtered[filtered.sentiment.isin(sentiments)]
    if review_only:
        filtered = filtered[filtered.needs_review == True]
    dates = pd.to_datetime(successful.date, errors='coerce', utc=True)
    if dates.notna().any():
        period = st.date_input('Period (UTC dates; undated reviews excluded)',
                               (dates.min().date(), dates.max().date()))
        if len(period) == 2:
            fd = pd.to_datetime(filtered.date, errors='coerce', utc=True).dt.date
            filtered = filtered[(fd >= period[0]) & (fd <= period[1])]
    else:
        st.caption('No dates mapped: time trends are unavailable.')
    st.dataframe(filtered[['review_id', 'theme', 'sentiment', 'severity', 'issue', 'evidence', 'needs_review', 'reviewed']],
                 hide_index=True, width='stretch')
    if not filtered.empty:
        rid = st.selectbox('Open original review', filtered.review_id.tolist(),
                          format_func=lambda rid: rid[:12] + ' · ' + filtered.loc[filtered.review_id == rid, 'text'].iloc[0][:70])
        current = filtered.loc[filtered.review_id == rid].iloc[0].to_dict()
        st.text(current['text'])
        st.caption('Evidence quote')
        st.text(current['evidence'])
        with st.expander('Review or correct classification'):
            st.caption('Corrections are appended to an audit trail; machine output is preserved. They are not automatically evaluation labels.')
            with st.form('correction_' + rid + config.key):
                theme = st.selectbox('Correct theme', THEMES, index=THEMES.index(current['theme']))
                sentiment = st.selectbox('Correct sentiment', SENTIMENTS, index=SENTIMENTS.index(current['sentiment']))
                severity = st.number_input('Reported severity (0–3)', 0, 3, int(current['severity']))
                issue = st.text_input('Reported issue (empty for severity 0)', current['issue'])
                evidence = st.text_area('Exact evidence quote', current['evidence'])
                confidence = st.slider('Confidence (heuristic)', 0.0, 1.0, float(current['confidence']))
                needs_review = st.checkbox('Still needs review', value=bool(current['needs_review']))
                reviewer = st.text_input('Reviewer')
                reason = st.text_input('Correction reason')
                if st.form_submit_button('Save review'):
                    try:
                        corrected = Classification(theme=theme, sentiment=sentiment, severity=severity, issue=issue,
                            evidence=evidence, confidence=confidence, needs_review=needs_review)
                        store.correct(rid, config.key, corrected, reviewer, reason)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
    st.subheader('Investigation priorities · current filters')
    st.caption('Score = sum of reported severity per unique review. Severity is an allegation, not a verified fact. Frequency denominator: successful reviews in the current filters. Pending/failed reviews are excluded; results may be biased.')
    ranked = priorities(filtered.to_dict('records'))
    if ranked:
        st.dataframe(ranked, hide_index=True, width='stretch')
    else:
        st.info('No reported problems in this selection.')

st.subheader('4. Export and inspect processing')
st.caption('Exports include all accepted reviews in this CSV, including pending/failed statuses and the active configuration. CSV formula prefixes are escaped; JSON preserves exact text.')
a, b, c = st.columns(3)
a.download_button('Results CSV', safe_csv(results), 'feedback_results.csv', 'text/csv')
b.download_button('Results + configuration JSON', json_export(results, config), 'feedback_results.json', 'application/json')
audit = store.audit(config.key)
c.download_button('Processing audit CSV', safe_csv(audit), 'processing_audit.csv', 'text/csv')
with st.expander('Configuration and execution audit'):
    st.json(config.model_dump())
    st.caption('Audit covers this configuration across local datasets. Failed API requests may consume tokens without returning usage; recorded totals are lower bounds.')
    st.dataframe(audit, hide_index=True, width='stretch')
    input_tokens = sum(r['input_tokens'] or 0 for r in audit)
    output_tokens = sum(r['output_tokens'] or 0 for r in audit)
    st.write(f'Recorded input tokens: {input_tokens} · output tokens: {output_tokens}')
    prices = [os.getenv('CFI_INPUT_PRICE'), os.getenv('CFI_OUTPUT_PRICE')]
    if is_llm and all(prices):
        try:
            cost = (input_tokens * float(prices[0]) + output_tokens * float(prices[1])) / 1_000_000
            st.write(f'Estimated USD cost for recorded usage: ${cost:.6f} (user-supplied prices; excludes unreported usage).')
        except ValueError:
            st.warning('Invalid token prices in environment.')
    else:
        st.caption('Dollar cost unavailable without verified prices and real API usage.')
