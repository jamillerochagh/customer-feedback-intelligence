from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Theme = Literal['product_quality', 'service', 'speed', 'price', 'other']
Sentiment = Literal['positive', 'negative', 'neutral', 'mixed', 'uncertain']
THEMES = list(Theme.__args__)
SENTIMENTS = list(Sentiment.__args__)
PROMPT_VERSION = 'classify-v1'
PROMPT = (Path(__file__).parent / 'prompts' / (PROMPT_VERSION + '.txt')).read_text()


class Classification(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    theme: Theme
    sentiment: Sentiment
    severity: int = Field(ge=0, le=3)
    issue: str = Field(max_length=500)
    evidence: str = Field(min_length=1, max_length=12000)
    confidence: float = Field(ge=0, le=1)
    needs_review: bool

    @model_validator(mode='after')
    def consistent(self):
        if self.severity > 0 and not self.issue.strip():
            raise ValueError('A reported problem requires an issue description')
        if self.severity == 0 and self.issue:
            raise ValueError('No-problem results must have an empty issue')
        if (self.sentiment == 'uncertain' or self.confidence < 0.7) and not self.needs_review:
            raise ValueError('Uncertain results require review')
        return self

    def grounded(self, text: str):
        if self.evidence not in text or not self.evidence.strip():
            raise ValueError('Evidence must be an exact nonblank substring of the review')
        return self


class AnalysisConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider: Literal['baseline', 'openai'] = 'baseline'
    model: str = 'keyword-v1'
    prompt_version: str = PROMPT_VERSION
    prompt_sha256: str = hashlib.sha256(PROMPT.encode()).hexdigest()
    schema_sha256: str = hashlib.sha256(json.dumps(Classification.model_json_schema(), sort_keys=True).encode()).hexdigest()
    temperature: float = 0.0
    max_completion_tokens: int = 700
    pipeline_version: str = '1'

    @property
    def key(self):
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


def review_id(text: str) -> str:
    """Exact UTF-8 text identity; duplicate texts count once, never silently normalized."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
