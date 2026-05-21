# Third-Party Image API

## Goal

Use a third-party image gateway without locking the skill to a single vendor-specific SDK. Favor HTTP adapters that can switch between Gemini-style and OpenAI-style request formats.

## Current Assumption

The gateway may expose one or both of these interfaces:

- Gemini-compatible `generateContent`
- OpenAI-compatible `chat/completions`

Known portal endpoints from the current account screenshots:

- Primary base URL: `https://api.viviai.cc`
- Backup base URL: `https://api.viviai.top`
- Candidate model ID: `gemini-3-pro-image-preview`
- Candidate model group: `nanobanana分组`

Treat the gateway as untrusted until a real request succeeds. Keep request and response dumps for debugging.

## Minimum Information Needed

- Base URL, for example `https://example.com`
- API key
- Authentication pattern
  - `Authorization: Bearer <key>`
  - `x-api-key: <key>`
  - query-string key
- Exact model ID
- Exact endpoint path
- Group routing rule if the account uses model groups
- One successful sample request body or curl snippet
- One successful sample response body with image data

## Default Environment Variables

- `P2D_IMAGE_API_BASE_URL`
- `P2D_IMAGE_API_KEY`
- `P2D_IMAGE_MODEL`
- `P2D_IMAGE_PROTOCOL`
- `P2D_IMAGE_GROUP`
- `P2D_IMAGE_GROUP_HEADER`
- `P2D_IMAGE_AUTH_MODE`

## Integration Rule

- Use the generic adapter script first.
- Keep the raw response body for the first successful call.
- Once the gateway behavior is proven, use the adapter only for explicit supplemental visual-asset requests, not for the default full-page production route.

## Guardrails

- Do not send thesis data to the image model unless the prompt is already reduced to the figure brief needed for that single asset.
- Prefer transparent background outputs for slide-page image overlays.
- Keep prompts and captions Chinese-first unless the user explicitly asks for English.
