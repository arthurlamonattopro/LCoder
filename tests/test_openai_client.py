"""Tests for utils.openai_client helpers."""
from utils.openai_client import OpenAIRequestError, extract_output_text, resolve_api_key


def test_resolve_api_key_returns_explicit_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert resolve_api_key("sk-explicit") == "sk-explicit"


def test_resolve_api_key_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert resolve_api_key(None) == "sk-from-env"
    assert resolve_api_key("") == "sk-from-env"


def test_resolve_api_key_returns_empty_when_nothing_set(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert resolve_api_key(None) == ""
    assert resolve_api_key("") == ""


def test_extract_output_text_handles_responses_api_shape():
    payload = {
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": "Hello world"},
                ],
            }
        ]
    }
    assert extract_output_text(payload) == "Hello world"


def test_extract_output_text_handles_refusal():
    payload = {
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_refusal", "refusal": "I can't help with that."},
                ],
            }
        ]
    }
    assert extract_output_text(payload) == "I can't help with that."


def test_extract_output_text_falls_back_to_chat_completions_shape():
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hi from chat completions",
                }
            }
        ]
    }
    assert extract_output_text(payload) == "Hi from chat completions"


def test_extract_output_text_handles_empty_payload():
    assert extract_output_text({}) == ""
    assert extract_output_text(None) == ""


def test_create_response_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from utils.openai_client import create_response

    try:
        create_response(api_key=None, model="gpt-4", user_text="hello")
        assert False, "Should have raised"
    except OpenAIRequestError as exc:
        assert "Missing API key" in str(exc)


def test_create_response_missing_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from utils.openai_client import create_response

    try:
        create_response(model=None, user_text="hello")
        assert False, "Should have raised"
    except OpenAIRequestError as exc:
        assert "Missing model" in str(exc)


def test_create_response_missing_prompt(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from utils.openai_client import create_response

    try:
        create_response(model="gpt-4", user_text="")
        assert False, "Should have raised"
    except OpenAIRequestError as exc:
        assert "Missing prompt" in str(exc)
