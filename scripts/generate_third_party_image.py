from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from common_io import ensure_parent, write_json


DEFAULT_BASE_ENV = "P2D_IMAGE_API_BASE_URL"
DEFAULT_KEY_ENV = "P2D_IMAGE_API_KEY"
DEFAULT_MODEL_ENV = "P2D_IMAGE_MODEL"
DEFAULT_PROTOCOL_ENV = "P2D_IMAGE_PROTOCOL"
DEFAULT_GROUP_ENV = "P2D_IMAGE_GROUP"
DEFAULT_GROUP_HEADER_ENV = "P2D_IMAGE_GROUP_HEADER"
DEFAULT_AUTH_MODE_ENV = "P2D_IMAGE_AUTH_MODE"
DEFAULT_AUTH_HEADER_ENV = "P2D_IMAGE_AUTH_HEADER"
DEFAULT_AUTH_PREFIX_ENV = "P2D_IMAGE_AUTH_PREFIX"


def env_or_value(value: str | None, env_name: str, fallback: str | None = None) -> str | None:
    if value:
        return value
    return os.environ.get(env_name, fallback)


def load_config(config_file: str | None) -> dict[str, Any]:
    if not config_file:
        return {}
    return json.loads(Path(config_file).read_text(encoding="utf-8"))


def config_env_or_value(
    value: str | None,
    config: dict[str, Any],
    config_key: str,
    env_name: str,
    fallback: str | None = None,
) -> str | None:
    if value:
        return value
    config_value = config.get(config_key)
    if config_value not in (None, ""):
        return str(config_value)
    return os.environ.get(env_name, fallback)


def config_extra_headers(config: dict[str, Any]) -> list[str]:
    raw = config.get("extra_headers")
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [f"{key}={value}" for key, value in raw.items()]
    if isinstance(raw, list):
        return [str(item) for item in raw]
    raise SystemExit("config.extra_headers must be an object or a list.")


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt.strip()
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    raise SystemExit("Either --prompt or --prompt-file is required.")


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def build_endpoint(protocol: str, base_url: str, model: str, endpoint: str | None) -> str:
    if endpoint:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"{normalize_base_url(base_url)}{endpoint}"
    if protocol == "gemini":
        return f"{normalize_base_url(base_url)}/v1beta/models/{model}:generateContent"
    if protocol == "openai":
        return f"{normalize_base_url(base_url)}/v1/chat/completions"
    raise SystemExit(f"Unsupported protocol: {protocol}")


def build_headers(
    api_key: str | None,
    auth_mode: str,
    group: str | None,
    group_header: str | None,
    auth_header: str | None,
    auth_prefix: str | None,
    extra_headers: list[str],
) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        if auth_mode == "bearer":
            headers[auth_header or "Authorization"] = f"{auth_prefix or 'Bearer'} {api_key}".strip()
        elif auth_mode == "header":
            headers[auth_header or "Authorization"] = f"{auth_prefix or ''}{api_key}"
        elif auth_mode == "x-api-key":
            headers[auth_header or "x-api-key"] = f"{auth_prefix or ''}{api_key}"
        elif auth_mode == "none":
            pass
        elif auth_mode == "query":
            pass
        else:
            raise SystemExit(f"Unsupported auth mode: {auth_mode}")
    if group and group_header:
        headers[group_header] = group
    for item in extra_headers:
        if "=" not in item:
            raise SystemExit(f"Invalid --extra-header value: {item}")
        key, value = item.split("=", 1)
        headers[key.strip()] = value.strip()
    return headers


def append_query_auth(url: str, api_key: str | None, auth_mode: str) -> str:
    if auth_mode != "query" or not api_key:
        return url
    parsed = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    pairs.append(("key", api_key))
    new_query = urllib.parse.urlencode(pairs)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))


def redact_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if "authorization" in lowered or "api-key" in lowered or lowered.endswith("key"):
            redacted[key] = "<REDACTED>"
        else:
            redacted[key] = value
    return redacted


def build_gemini_payload(prompt: str, model: str, args: argparse.Namespace) -> dict[str, Any]:
    generation_config: dict[str, Any] = {
        "responseModalities": ["Image"],
    }
    if args.aspect_ratio:
        generation_config["imageConfig"] = {"aspectRatio": args.aspect_ratio}
    if args.image_size:
        generation_config.setdefault("imageConfig", {})["imageSize"] = args.image_size

    text = prompt
    if args.transparent_background:
        text += "\n要求：透明背景，适合叠加到答辩页面图像中。"

    return {
        "model": model,
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": text},
                ],
            }
        ],
        "generationConfig": generation_config,
    }


def build_openai_payload(prompt: str, model: str, args: argparse.Namespace) -> dict[str, Any]:
    text = prompt
    if args.transparent_background:
        text += "\nRequirement: transparent background, suitable for slide-page image overlay."

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                ],
            }
        ],
    }
    if args.image_size:
        payload["image_size"] = args.image_size
    if args.aspect_ratio:
        payload["aspect_ratio"] = args.aspect_ratio
    if args.output_modalities:
        payload["modalities"] = args.output_modalities.split(",")
    return payload


def build_payload(protocol: str, prompt: str, model: str, args: argparse.Namespace) -> dict[str, Any]:
    if args.raw_body_file:
        return json.loads(Path(args.raw_body_file).read_text(encoding="utf-8"))
    if protocol == "gemini":
        return build_gemini_payload(prompt, model, args)
    if protocol == "openai":
        return build_openai_payload(prompt, model, args)
    raise SystemExit(f"Unsupported protocol: {protocol}")


def extract_base64_candidates(node: Any, hits: list[tuple[str, str, str]]) -> None:
    if isinstance(node, dict):
        if "inlineData" in node and isinstance(node["inlineData"], dict):
            data = node["inlineData"].get("data")
            mime = node["inlineData"].get("mimeType", "image/png")
            if isinstance(data, str):
                hits.append(("inlineData.data", data, mime))
        for key in ("b64_json", "image_base64", "base64"):
            value = node.get(key)
            if isinstance(value, str):
                hits.append((key, value, node.get("mime_type", "image/png")))
        for value in node.values():
            extract_base64_candidates(value, hits)
    elif isinstance(node, list):
        for item in node:
            extract_base64_candidates(item, hits)


def extract_url_candidates(node: Any, hits: list[str]) -> None:
    if isinstance(node, dict):
        for key in ("url", "image_url"):
            value = node.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                hits.append(value)
        for value in node.values():
            extract_url_candidates(value, hits)
    elif isinstance(node, list):
        for item in node:
            extract_url_candidates(item, hits)


def detect_suffix(mime_type: str | None, output_file: Path) -> str:
    if output_file.suffix:
        return output_file.suffix
    return mimetypes.guess_extension(mime_type or "image/png") or ".png"


def save_base64_image(b64_data: str, mime_type: str | None, output_file: Path) -> Path:
    image_bytes = base64.b64decode(b64_data)
    suffix = detect_suffix(mime_type, output_file)
    target = output_file if output_file.suffix else output_file.with_suffix(suffix)
    ensure_parent(target)
    target.write_bytes(image_bytes)
    return target


def download_image(url: str, output_file: Path) -> Path:
    ensure_parent(output_file)
    with urllib.request.urlopen(url) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type", "image/png")
    suffix = detect_suffix(content_type, output_file)
    target = output_file if output_file.suffix else output_file.with_suffix(suffix)
    target.write_bytes(payload)
    return target


def send_json_request(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} calling image API.\n{body}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Call a third-party image API using Gemini-style or OpenAI-style HTTP requests.")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    parser.add_argument("--output-file", required=True)
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
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--image-size")
    parser.add_argument("--output-modalities", help="Comma-separated list, mainly for OpenAI-compatible gateways.")
    parser.add_argument("--transparent-background", action="store_true")
    parser.add_argument("--raw-body-file", help="Send a raw JSON body from file instead of using the built-in template.")
    parser.add_argument("--request-dump-file")
    parser.add_argument("--response-dump-file")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    config = load_config(args.config_file)
    prompt = "" if args.raw_body_file else load_prompt(args)
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

    endpoint_url = build_endpoint(protocol, base_url, model, args.endpoint)
    endpoint_url = append_query_auth(endpoint_url, api_key, auth_mode)
    headers = build_headers(api_key, auth_mode, group, group_header, auth_header, auth_prefix, merged_extra_headers)
    payload = build_payload(protocol, prompt, model, args)

    request_preview = {
        "protocol": protocol,
        "url": endpoint_url,
        "headers": redact_sensitive_headers(headers),
        "payload": payload,
    }

    if args.request_dump_file:
        write_json(Path(args.request_dump_file), request_preview)

    if args.dry_run:
        print(json.dumps(request_preview, ensure_ascii=False, indent=2))
        return

    status, response_json = send_json_request(endpoint_url, headers, payload, args.timeout)
    if args.response_dump_file:
        write_json(Path(args.response_dump_file), response_json)

    base64_hits: list[tuple[str, str, str]] = []
    url_hits: list[str] = []
    extract_base64_candidates(response_json, base64_hits)
    extract_url_candidates(response_json, url_hits)

    output_file = Path(args.output_file)
    if base64_hits:
        saved = save_base64_image(base64_hits[0][1], base64_hits[0][2], output_file)
        print(json.dumps({"status": status, "saved_to": str(saved), "source": base64_hits[0][0]}, ensure_ascii=False))
        return
    if url_hits:
        saved = download_image(url_hits[0], output_file)
        print(json.dumps({"status": status, "saved_to": str(saved), "source": "url"}, ensure_ascii=False))
        return

    if args.response_dump_file:
        raise SystemExit(
            "No image payload was detected in the response. "
            f"Inspect {args.response_dump_file} and adjust protocol or raw body."
        )
    print(json.dumps(response_json, ensure_ascii=False, indent=2))
    raise SystemExit("No image payload was detected in the response.")


if __name__ == "__main__":
    main()
