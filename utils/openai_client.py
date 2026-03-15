import json
import urllib.error
import urllib.request


class OpenAIRequestError(Exception):
    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


def create_response(api_key, model, user_text, system_text=None, timeout=60):
    if not api_key:
        raise OpenAIRequestError("Missing API key.")
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
    req.add_header("Authorization", f"Bearer {api_key}")

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
    if not isinstance(response_json, dict):
        return ""
    output = response_json.get("output") or []
    chunks = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
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
            elif part.get("type") == "output_refusal":
                refusal = part.get("refusal")
                if refusal:
                    chunks.append(refusal)
    return "\n".join(chunks).strip()
