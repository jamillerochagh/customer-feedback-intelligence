import json

import pandas as pd


def safe_csv(rows):
    """Escape spreadsheet formula prefixes, including after whitespace; originals stay in JSON/DB."""
    frame = pd.DataFrame(rows)
    def escape(value):
        if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
            return "'" + value
        return value
    for col in frame.columns:
        frame[col] = frame[col].map(escape)
    return frame.to_csv(index=False).encode('utf-8')


def priorities(rows):
    successful = [r for r in rows if r.get('status') == 'success']
    denominator = len(successful)
    output = []
    for theme in sorted({r['theme'] for r in successful if r['severity'] > 0}):
        problems = [r for r in successful if r['theme'] == theme and r['severity'] > 0]
        output.append({
            'theme': theme, 'reported_problems': len(problems),
            'share_of_analyzed': len(problems) / denominator,
            'max_reported_severity': max(r['severity'] for r in problems),
            'priority_score': sum(r['severity'] for r in problems),
            'needs_review': sum(bool(r['needs_review']) for r in problems),
            'evidence_ids': ', '.join(r['review_id'] for r in problems),
            'action_hypothesis': 'Investigate ' + theme + ' examples and verify the reported failure before choosing an intervention.',
            'verification_plan': 'Manually confirm cases; measure the same complaint rate per unique review in comparable windows, with volume and rating mix. Use a controlled experiment for causal impact.',
        })
    return sorted(output, key=lambda r: (-r['priority_score'], r['theme']))


def json_export(rows, config):
    return json.dumps({'config': config.model_dump(), 'rows': rows}, ensure_ascii=False, indent=2).encode()
