from __future__ import annotations

import argparse
from pathlib import Path

from common_io import read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a placeholder Google render plan from a deck spec.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--template", default="academic-elegance")
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    payload = {
        "schema_version": "0.1",
        "status": "placeholder",
        "message": "Google Slides rendering is intentionally deferred in the scaffold. Use the local renderer for smoke tests.",
        "title": spec.get("title"),
        "template": args.template,
        "slide_count": len(spec.get("slides", []))
    }
    write_json(Path(args.output_file), payload)


if __name__ == "__main__":
    main()
