from cfi.providers import ProviderError, classify_with_retry


def analyze(rows, config, provider, store, progress=None):
    store.register(config)
    counts = {'success': 0, 'cached': 0, 'failed': 0}
    for index, row in enumerate(rows):
        cached = store.get(row['review_id'], config.key)
        if cached and cached['status'] == 'success':
            counts['cached'] += 1
        else:
            def record(number, status, error, latency, result):
                store.attempt(row['review_id'], config.key, number, status, error, latency, result)
            try:
                result = classify_with_retry(provider, row['text'], record)
            except ProviderError as exc:
                store.save(row, config.key, error=str(exc))
                counts['failed'] += 1
            else:
                store.save(row, config.key, result)
                counts['success'] += 1
        if progress:
            progress((index + 1) / len(rows))
    return counts
