"""Thin wrapper around an OpenAI-compatible chat-completions API (e.g. Core42/G42 Compass)."""
from __future__ import annotations

import json
import os

from openai import OpenAI

DEFAULT_MODEL = os.environ.get("ARCH_COMPLIANCE_MODEL", "gpt-4o")

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ.get("COMPASS_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("COMPASS_BASE_URL") or os.environ.get("OPENAI_BASE_URL"),
        )
    return _client


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def call_json(
    model: str,
    system: str,
    user_text: str,
    max_tokens: int = 4000,
    image_b64_list: list[str] | None = None,
):
    """Call the model and parse a JSON response. Raises if the response isn't valid JSON."""
    content: list[dict] = [{"type": "text", "text": user_text}]
    for image_b64 in image_b64_list or []:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            }
        )

    response = get_client().chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
    )
    text = _strip_fences(response.choices[0].message.content or "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\n---\n{text[:2000]}") from e
