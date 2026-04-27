from __future__ import annotations

import argparse
import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

from common_io import ensure_parent, write_json, write_text
from generate_third_party_image import (
    DEFAULT_AUTH_HEADER_ENV,
    DEFAULT_AUTH_MODE_ENV,
    DEFAULT_AUTH_PREFIX_ENV,
    DEFAULT_BASE_ENV,
    DEFAULT_GROUP_ENV,
    DEFAULT_GROUP_HEADER_ENV,
    DEFAULT_KEY_ENV,
    DEFAULT_MODEL_ENV,
    DEFAULT_PROTOCOL_ENV,
    append_query_auth,
    build_endpoint,
    build_headers,
    config_env_or_value,
    config_extra_headers,
    load_config,
    load_prompt,
    redact_sensitive_headers,
    send_json_request,
)


def inline_part(path: Path) -> dict[str, Any]:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime_type, "data": payload}}


def build_text_payload(prompt: str, inline_files: list[Path]) -> dict[str, Any]:
    parts: list[dict[str, Any]] = [{"text": prompt}]
    parts.extend(inline_part(path) for path in inline_files)
    return {
        "contents": [
            {
                "role": "user",
                "parts": parts,
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT"],
        },
    }


def extract_text_candidates(node: Any, hits: list[str]) -> None:
    if isinstance(node, dict):
        text = node.get("text")
        if isinstance(text, str) and text.strip():
            hits.append(text.strip())
        content = node.get("content")
        if isinstance(content, str) and content.strip():
            hits.append(content.strip())
        for value in node.values():
            extract_text_candidates(value, hits)
    elif isinstance(node, list):
        for item in node:
            extract_text_candidates(item, hits)


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return cleaned


def parse_json_text(text: str) -> Any:
    cleaned = strip_code_fence(text)
    return json.loads(cleaned)


def main() -> None:
    parser = argparse.ArgumentParser(description="Call a third-party Gemini/OpenAI-style model for text or JSON responses.")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--config-file")
    parser.add_argument("--protocol", choices=["gemini", "openai"], default=None)
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key")
    parser.add_argument("--auth-mode", choices=["bearer", "header", "x-api-key", "query", "none"], default=None)
    parser.add_argument("--auth-header")
    parser.add_argument("--auth-prefix")
    parser.add_argument("--group")
    parser.add_argument("--group-header")
    parser.add_argument("--extra-header", action="append", default=[])
    parser.add_argument("--inline-file", action="append", default=[])
    parser.add_argument("--raw-body-file")
    parser.add_argument("--output-json")
    parser.add_argument("--output-text-file")
    parser.add_argument("--request-dump-file")
    parser.add_argument("--response-dump-file")
    parser.add_argument("--expect-json", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    config = load_config(args.config_file)
    protocol = config_env_or_value(args.protocol, config, "protocol", DEFAULT_PROTOCOL_ENV, "gemini")
    base_url = config_env_or_value(args.base_url, config, "base_url", DEFAULT_BASE_ENV)
    model = config_env_or_value(args.model, config, "model", DEFAULT_MODEL_ENV)
    api_key = config_env_or_value(args.api_key, config, "api_key", DEFAULT_KEY_ENV)
    auth_mode = config_env_or_value(args.auth_mode, config, "auth_mode", DEFAULT_AUTH_MODE_ENV, "bearer")
    group = config_env_or_value(args.group, config, "group", DEFAULT_GROUP_ENV)
    group_header = config_env_or_value(args.group_header, config, "group_header", DEFAULT_GROUP_HEADER_ENV, "X-API-Group")
    auth_header = config_env_or_value(args.auth_header, config, "auth_header", DEFAULT_AUTH_HEADER_ENV)
    auth_prefix = config_env_or_value(args.auth_prefix, config, "auth_prefix", DEFAULT_AUTH_PREFIX_ENV)
    merged_extra_headers = [*config_extra_headers(config), *args.extra_header]

    if not base_url:
        raise SystemExit(f"Missing base URL. Set --base-url or {DEFAULT_BASE_ENV}.")
    if not model:
        raise SystemExit(f"Missing model. Set --model or {DEFAULT_MODEL_ENV}.")

    prompt = "" if args.raw_body_file else load_prompt(args)
    endpoint_url = build_endpoint(protocol, base_url, model, args.endpoint)
    endpoint_url = append_query_auth(endpoint_url, api_key, auth_mode)
    headers = build_headers(api_key, auth_mode, group, group_header, auth_header, auth_prefix, merged_extra_headers)
    inline_files = [Path(item).resolve() for item in args.inline_file]

    if args.raw_body_file:
        payload = json.loads(Path(args.raw_body_file).read_text(encoding="utf-8"))
    else:
        payload = build_text_payload(prompt, inline_files)

    request_preview = {
        "protocol": protocol,
        "url": endpoint_url,
        "headers": redact_sensitive_headers(headers),
        "payload": payload,
    }
    if args.request_dump_file:
        write_json(Path(args.request_dump_file), request_preview)

    status, response_json = send_json_request(endpoint_url, headers, payload, args.timeout)
    if args.response_dump_file:
        write_json(Path(args.response_dump_file), response_json)

    text_hits: list[str] = []
    extract_text_candidates(response_json, text_hits)
    if not text_hits:
        raise SystemExit("No text payload was detected in the response.")

    primary_text = text_hits[0]
    result: Any = primary_text
    if args.expect_json:
        result = parse_json_text(primary_text)

    if args.output_text_file:
        write_text(Path(args.output_text_file), primary_text)
    if args.output_json:
        write_json(Path(args.output_json), {"status": status, "result": result, "raw_text": primary_text})
    else:
        print(json.dumps({"status": status, "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
