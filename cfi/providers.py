from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from cfi.models import AnalysisConfig, Classification, PROMPT


@dataclass
class ProviderResult:
    classification: Classification
    input_tokens: int = 0
    output_tokens: int = 0
    actual_model: str = 'keyword-v1'


class ProviderError(Exception):
    """Safe error code: never persist headers, keys, or response bodies."""


class Provider(Protocol):
    def classify(self, text: str) -> ProviderResult: ...


class Baseline:
    """Deliberately weak, English-only lexical baseline. Never an LLM simulation."""
    groups = {
        'product_quality': ['food', 'taste', 'tasty', 'steak', 'chicken', 'pizza', 'cold', 'delicious'],
        'service': ['staff', 'service', 'waiter', 'waitress', 'rude', 'friendly'],
        'speed': ['slow', 'wait', 'waiting', 'minutes', 'late', 'delivery'],
        'price': ['price', 'expensive', 'cheap', 'money', 'value', 'refund'],
    }
    positives = ['good', 'great', 'excellent', 'amazing', 'delicious', 'friendly', 'love', 'tasty']
    negatives = ['bad', 'terrible', 'awful', 'rude', 'slow', 'cold', 'poor', 'disappointed', 'horrible']

    def classify(self, text):
        words = set(re.findall(r"[a-z]+", text.lower()))
        scores = {k: len(words.intersection(v)) for k, v in self.groups.items()}
        best = max(scores, key=scores.get)
        theme = best if scores[best] else 'other'
        pos, neg = bool(words.intersection(self.positives)), bool(words.intersection(self.negatives))
        sentiment = 'mixed' if pos and neg else 'positive' if pos else 'negative' if neg else 'uncertain'
        result = Classification(theme=theme, sentiment=sentiment, severity=1 if neg else 0,
                                issue='Negative keyword detected; human interpretation required.' if neg else '',
                                evidence=text, confidence=0.4, needs_review=True)
        return ProviderResult(result)


class OpenAIProvider:
    def __init__(self, key: str, config: AnalysisConfig, client=None):
        if not key:
            raise ValueError('OPENAI_API_KEY is required for real LLM analysis')
        self.key, self.config = key, config
        self.client = client or httpx.Client(timeout=httpx.Timeout(30, connect=10))

    def classify(self, text):
        payload = {
            'model': self.config.model,
            'messages': [{'role': 'system', 'content': PROMPT},
                         {'role': 'user', 'content': json.dumps({'review_text': text}, ensure_ascii=False)}],
            'temperature': self.config.temperature,
            'max_completion_tokens': self.config.max_completion_tokens,
            'store': False,
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'feedback_classification', 'strict': True,
                'schema': Classification.model_json_schema()}},
        }
        try:
            response = self.client.post('https://api.openai.com/v1/chat/completions', json=payload,
                                        headers={'Authorization': 'Bearer ' + self.key})
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ProviderError('transient_transport') from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise ProviderError('transient_http_' + str(response.status_code))
        if response.status_code != 200:
            raise ProviderError('http_' + str(response.status_code))
        try:
            body = response.json()
            choice = body['choices'][0]
            if choice['message'].get('refusal'):
                raise ProviderError('refused')
            if choice['finish_reason'] != 'stop':
                raise ProviderError('incomplete_response')
            result = Classification.model_validate_json(choice['message']['content']).grounded(text)
            usage = body.get('usage', {})
            return ProviderResult(result, usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0), body['model'])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError('invalid_response') from exc

    def close(self):
        self.client.close()


def classify_with_retry(provider, text, on_attempt, sleep=time.sleep):
    for attempt in range(1, 4):
        start = time.perf_counter()
        try:
            result = provider.classify(text)
            result.classification.grounded(text)
        except (ProviderError, ValueError) as exc:
            code = str(exc) if isinstance(exc, ProviderError) else 'invalid_response'
            on_attempt(attempt, 'failed', code, time.perf_counter() - start, None)
            if not code.startswith('transient_') or attempt == 3:
                raise ProviderError(code) from exc
            sleep(2 ** (attempt - 1))
        else:
            on_attempt(attempt, 'success', None, time.perf_counter() - start, result)
            return result
