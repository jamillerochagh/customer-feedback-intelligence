"""Download once, deterministically split, and record provenance. Never upload data."""
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import urllib.request
import zipfile

from cfi.models import review_id

URL = 'https://archive.ics.uci.edu/static/public/331/sentiment+labelled+sentences.zip'
ROOT = Path(__file__).resolve().parents[1]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, help='Use an already downloaded UCI ZIP')
    args = parser.parse_args()
    raw = args.archive.read_bytes() if args.archive else urllib.request.urlopen(URL, timeout=30).read()
    archive = zipfile.ZipFile(io.BytesIO(raw))
    member = next(n for n in archive.namelist() if n.endswith('/yelp_labelled.txt') and not n.startswith('__MACOSX'))
    records, seen = [], set()
    for number, line in enumerate(archive.read(member).decode('utf-8').splitlines(), 1):
        text, label = line.rsplit('\t', 1)
        rid = review_id(text)
        if rid not in seen:
            records.append({'review_id': rid, 'text': text, 'source_line': number,
                            'sentiment_gold': 'positive' if label == '1' else 'negative'})
            seen.add(rid)
    random.Random(42).shuffle(records)
    root = ROOT / 'data'
    root.mkdir(exist_ok=True)
    def write(name, rows, fields):
        with (root / name).open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
    write('demo.csv', records[:30], ['review_id', 'text', 'source_line'])
    write('evaluation.csv', records[30:90], ['review_id', 'text', 'source_line', 'sentiment_gold'])
    review_rows = [dict(r, theme_gold='', severity_gold='', evidence_gold='', annotator='', annotation_status='pending', notes='') for r in records[30:90]]
    write('human_review.csv', review_rows,
          ['review_id', 'text', 'theme_gold', 'severity_gold', 'evidence_gold', 'annotator', 'annotation_status', 'notes'])
    (root / 'provenance.json').write_text(json.dumps({
        'dataset': 'Sentiment Labelled Sentences', 'creator': 'Dimitrios Kotzias', 'year': 2015,
        'doi': 'https://doi.org/10.24432/C57604', 'url': URL,
        'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'archive_sha256': hashlib.sha256(raw).hexdigest(), 'member': member, 'seed': 42,
        'transformations': 'Yelp subset; exact text deduplication; seeded shuffle; 30 demo and 60 disjoint evaluation sentences; binary labels mapped to words. No dates/ratings invented.',
        'files_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                         for name in ['demo.csv', 'evaluation.csv', 'human_review.csv']},
    }, indent=2) + '\n')
    print('Prepared 30 demo and 60 held-out reviews; human annotation is pending.')


if __name__ == '__main__':
    main()
