from streamlit.testing.v1 import AppTest


def test_sample_baseline_and_export(tmp_path, monkeypatch):
    monkeypatch.setenv('CFI_DB', str(tmp_path / 'ui.sqlite'))
    app = AppTest.from_file('app.py', default_timeout=30).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert any('New successes: 30' in str(x.value) for x in app.success)
    assert len(app.dataframe) >= 2
    app.button[0].click().run()
    assert not app.exception
    assert any('cached: 30' in str(x.value) for x in app.success)


def test_llm_without_key(tmp_path, monkeypatch):
    monkeypatch.setenv('CFI_DB', str(tmp_path / 'ui.sqlite'))
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    app = AppTest.from_file('app.py', default_timeout=30).run()
    app.selectbox(key='engine').select('OpenAI · real LLM').run()
    assert not app.exception
    assert app.button[0].disabled
