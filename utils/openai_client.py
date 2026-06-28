import json
import os
import urllib.error
import urllib.request


class OpenAIRequestError(Exception):
    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


def resolve_api_key(explicit_key=None):
    """Resolve the OpenAI API key.

    Priority order:
    1. Explicit key passed by the caller (e.g. from the UI field).
    2. ``OPENAI_API_KEY`` environment variable.
    Returns an empty string if nothing is found.
    """
    if explicit_key:
        return explicit_key
    return os.environ.get("OPENAI_API_KEY", "")


def create_response(api_key=None, model=None, user_text=None, system_text=None, timeout=60):
    """Send a request to the OpenAI Responses API.

    ``api_key`` is optional: if omitted, falls back to the
    ``OPENAI_API_KEY`` environment variable.
    """
    resolved_key = resolve_api_key(api_key)
    if not resolved_key:
        raise OpenAIRequestError(
            "Missing API key. Set OPENAI_API_KEY env var or pass api_key explicitly."
        )
    if not model:
        raise OpenAIRequestError("Missing model.")
    if not user_text:
        raise OpenAIRequestError("Missing prompt.")

    payload = {"model": model}
    if system_text:
        payload["input"] = [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_text}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        ]
    else:
        payload["input"] = user_text

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=data,
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {resolved_key}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        raise OpenAIRequestError(
            f"OpenAI API error ({exc.code})",
            status=exc.code,
            body=body,
        ) from exc
    except urllib.error.URLError as exc:
        raise OpenAIRequestError(f"Network error: {exc.reason}") from exc


def extract_output_text(response_json):
    """Extract assistant text from a Responses API payload.

    Handles ``output_text``, ``output_refusal`` and the older
    ``message -> content -> text`` shape for robustness.
    """
    if not isinstance(response_json, dict):
        return ""

    # Newer Responses API: top-level ``output`` list of message items.
    output = response_json.get("output") or []
    chunks = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") not in (None, "message"):
            continue
        if item.get("role") != "assistant":
            continue
        content = item.get("content") or []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text":
                text = part.get("text")
                if text:
                    chunks.append(text)
            elif part.get("type") == "text":
                text = part.get("text")
                if text:
                    chunks.append(text)
            elif part.get("type") == "output_refusal":
                refusal = part.get("refusal")
                if refusal:
                    chunks.append(refusal)
    if chunks:
        return "\n".join(chunks).strip()

    # Fallback: Chat Completions-style ``choices[].message.content``.
    choices = response_json.get("choices") or []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content:
            chunks.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("text"):
                    chunks.append(part["text"])

    return "\n".join(chunks).strip()
