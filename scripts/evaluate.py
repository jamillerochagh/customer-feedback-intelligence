"""Evaluate raw machine outputs only; never train or score against self-generated labels."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics

from dotenv import load_dotenv

from cfi.ingest import map_rows, read_csv
from cfi.models import AnalysisConfig, THEMES
from cfi.pipeline import analyze
from cfi.providers import Baseline, OpenAIProvider
from cfi.store import Store

ROOT = Path(__file__).resolve().parents[1]


def classification_metrics(pairs, labels):
    # An abstention/unknown counts as a miss, not an excluded example.
    details = {}
    for label in labels:
        tp = sum(g == label and p == label for g, p in pairs)
        fp = sum(g != label and p == label for g, p in pairs)
        fn = sum(g == label and p != label for g, p in pairs)
        details[str(label)] = {'precision': tp / (tp + fp) if tp + fp else 0,
                              'recall': tp / (tp + fn) if tp + fn else 0,
                              'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
                              'support': sum(g == label for g, _ in pairs)}
    return {'n': len(pairs),
            'accuracy': sum(g == p for g, p in pairs) / len(pairs) if pairs else None,
            'macro_f1': statistics.mean(d['f1'] for d in details.values()),
            'per_class': details,
            'confusion': {str(g) + ' -> ' + str(p): n for (g, p), n in Counter(pairs).items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=['baseline', 'openai'], default='baseline')
    parser.add_argument('--output', type=Path, default=ROOT / 'local/evaluation')
    parser.add_argument('--human-labels', type=Path)
    args = parser.parse_args()
    load_dotenv(ROOT / '.env')
    if args.engine == 'openai' and not os.getenv('OPENAI_API_KEY'):
        parser.error('OPENAI_API_KEY required. No real LLM results have been produced.')
    args.output.mkdir(parents=True, exist_ok=True)
    config = AnalysisConfig(provider=args.engine,
        model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini-2025-04-14') if args.engine == 'openai' else 'keyword-v1')
    raw = (ROOT / 'data/evaluation.csv').read_bytes()
    gold = read_csv(raw)
    rows, rejected = map_rows(gold, 'text')
    assert not rejected
    # Separate database: this evaluation never sees UI corrections or demo outputs.
    store = Store(args.output / 'evaluation.sqlite')
    provider = OpenAIProvider(os.environ['OPENAI_API_KEY'], config) if args.engine == 'openai' else Baseline()
    try:
        counts = analyze(rows, config, provider, store)
    finally:
        if args.engine == 'openai':
            provider.close()
    predictions = store.export(rows, config.key, include_corrections=False)
    lookup = {r['review_id']: r for r in predictions}
    pairs = [(r.sentiment_gold, lookup[r.review_id].get('sentiment', 'failed')) for r in gold.itertuples()]
    report = {
        'created_at': datetime.now(timezone.utc).isoformat(), 'engine': args.engine,
        'config': config.model_dump(), 'config_id': config.key,
        'evaluation_sha256': hashlib.sha256(raw).hexdigest(),
        'reference': 'Independent binary sentiment labels from UCI / Kotzias (2015). Theme/severity require separate human annotation.',
        'processing': counts, 'sentiment': classification_metrics(pairs, ['positive', 'negative']),
        'abstention_rate': sum(p == 'uncertain' for _, p in pairs) / len(pairs),
        'failure_rate': sum(p == 'failed' for _, p in pairs) / len(pairs),
        'human_evaluation': {'status': 'pending', 'reviewed_rows': 0},
    }
    if args.human_labels:
        human = read_csv(args.human_labels.read_bytes())
        completed = human[human.annotation_status == 'reviewed']
        seen = set()
        theme_pairs, severity_pairs = [], []
        for r in completed.itertuples():
            if r.review_id not in lookup or r.review_id in seen or r.theme_gold not in THEMES or r.severity_gold not in ['0', '1', '2', '3'] or not r.annotator.strip():
                raise ValueError('Human labels require unique held-out IDs, valid labels, and a named independent annotator')
            prediction = lookup[r.review_id]
            if r.text != prediction['text'] or not r.evidence_gold.strip() or r.evidence_gold not in r.text:
                raise ValueError('Human evidence and text must match the held-out review')
            seen.add(r.review_id)
            theme_pairs.append((r.theme_gold, prediction.get('theme', 'failed')))
            severity_pairs.append((int(r.severity_gold), prediction.get('severity', 'failed')))
        if seen:
            report['human_evaluation'] = {'status': 'partial' if len(seen) < len(rows) else 'complete',
                'reviewed_rows': len(seen), 'labels_sha256': hashlib.sha256(args.human_labels.read_bytes()).hexdigest(),
                'theme': classification_metrics(theme_pairs, THEMES),
                'severity': classification_metrics(severity_pairs, [0, 1, 2, 3])}
    audit = store.audit(config.key)
    latencies = sorted(r['latency_seconds'] for r in audit)
    report['execution'] = {
        'recorded_attempts': len(audit),
        'median_attempt_seconds': statistics.median(latencies) if latencies else None,
        'p95_attempt_seconds': latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))] if latencies else None,
        'input_tokens_recorded': sum(r['input_tokens'] or 0 for r in audit),
        'output_tokens_recorded': sum(r['output_tokens'] or 0 for r in audit),
        'cost_usd': None,
        'note': 'Attempt latency includes provider and validation, excludes backoff/UI. Usage is a lower bound if requests failed. No dollar cost inferred.',
    }
    errors = []
    for r in gold.itertuples():
        p = lookup[r.review_id]
        if p.get('sentiment') != r.sentiment_gold:
            errors.append({'review_id': r.review_id, 'text': r.text, 'reference': r.sentiment_gold,
                           'prediction': p.get('sentiment', 'failed')})
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.output / 'errors.json').write_text(json.dumps(errors, indent=2) + '\n')
    (args.output / 'predictions.json').write_text(json.dumps({'config': config.model_dump(), 'rows': predictions}, indent=2) + '\n')
    (args.output / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps({'sentiment': report['sentiment'], 'human_evaluation': report['human_evaluation']}, indent=2))


if __name__ == '__main__':
    main()
