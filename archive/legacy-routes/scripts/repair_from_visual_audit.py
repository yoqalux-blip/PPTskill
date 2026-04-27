from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

from common_io import read_json, write_json


def shorten(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    for sep in ["：", "，", "；", "。", ",", ";"]:
        if sep in clean:
            head = clean.split(sep)[0]
            if 6 <= len(head) <= limit:
                return head
    return clean[: max(0, limit - 1)] + "…"


def compact_body_lines(lines: list[str], limit: int = 14) -> list[str]:
    compacted = [shorten(line, limit) for line in lines[:2]]
    return compacted or lines


def repair_gemini_hybrid(slide: dict[str, Any], issue_types: set[str]) -> bool:
    hybrid = slide.get("gemini_hybrid")
    if not hybrid:
        return False
    schema = hybrid.get("layout_schema")
    if not isinstance(schema, dict):
        return False

    qa_state = hybrid.setdefault("qa_state", {})
    schema_repairs = int(qa_state.get("schema_repair_count", 0))
    if schema_repairs == 0:
        qa_state["schema_repair_count"] = 1
        qa_state["request_regenerate_asset"] = False
        schema["density_mode"] = "compact"
        if "connector-text-overlap" in issue_types or "text-overlap" in issue_types:
            schema["connector_style"] = "outer"
        if schema.get("page_kind") == "study-board":
            for card in schema.get("cards", []):
                card["h"] = round(float(card.get("h", 0.72)) + 0.06, 2)
        if schema.get("page_kind") == "route-board":
            for card in schema.get("cards", []):
                if str(card.get("id", "")).startswith("output-"):
                    card["w"] = round(float(card.get("w", 2.52)) - 0.08, 2)
                else:
                    card["h"] = round(float(card.get("h", 1.0)) + 0.06, 2)
            center_hub = schema.get("canvas_regions", {}).get("center_hub")
            if isinstance(center_hub, dict):
                center_hub["h"] = round(float(center_hub.get("h", 1.84)) + 0.08, 2)
        if schema.get("page_kind") == "evidence-board":
            center_hub = schema.get("canvas_regions", {}).get("center_hub")
            if isinstance(center_hub, dict):
                center_hub["h"] = round(float(center_hub.get("h", 0.94)) + 0.08, 2)
        if schema.get("page_kind") == "mechanism-board":
            bridge = schema.get("canvas_regions", {}).get("bridge")
            if isinstance(bridge, dict):
                bridge["y"] = round(float(bridge.get("y", 4.84)) + 0.08, 2)
        return True

    qa_state["request_regenerate_asset"] = True
    qa_state["next_action"] = "regenerate-assets"
    return True


def apply_repairs(spec: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    repaired = copy.deepcopy(spec)
    issues_by_slide = {
        slide["slide_number"]: slide["issues"]
        for slide in audit.get("slides", [])
        if slide.get("issues")
    }

    for idx, slide in enumerate(repaired.get("slides", []), start=1):
        issues = issues_by_slide.get(idx, [])
        if not issues:
            continue
        issue_types = {issue["type"] for issue in issues}

        if repair_gemini_hybrid(slide, issue_types):
            continue

        if slide.get("takeaway"):
            slide["takeaway"] = shorten(slide["takeaway"], 28)
        if slide.get("bullets"):
            slide["bullets"] = [shorten(item, 28) for item in slide["bullets"][:3]]

        if slide.get("diagram_v5", {}).get("kind") == "study-board":
            if "text-overlap" in issue_types or "clipping-risk" in issue_types:
                slide["diagram_v5"]["summary"] = shorten(slide["diagram_v5"]["summary"], 28)
                slide["diagram_v5"]["bottom_chips"] = slide["diagram_v5"]["bottom_chips"][:3]
                for card in slide["diagram_v5"]["cards"]:
                    card["body"] = compact_body_lines(card.get("body", []), 12)

        if slide.get("diagram_v5", {}).get("kind") == "route-board":
            if "density-high" in issue_types or "clipping-risk" in issue_types:
                slide["diagram_v5"]["summary"] = shorten(slide["diagram_v5"]["summary"], 30)
                slide["diagram_v5"]["outputs"] = slide["diagram_v5"]["outputs"][:2]
                slide["diagram_v5"]["center"]["body"] = shorten(slide["diagram_v5"]["center"]["body"], 32)
                for card in slide["diagram_v5"]["cards"]:
                    card["body"] = compact_body_lines(card.get("body", []), 12)

        if slide.get("diagram_v5", {}).get("kind") == "evidence-board":
            slide["diagram_v5"]["summary"] = shorten(slide["diagram_v5"]["summary"], 28)
            slide["diagram_v5"]["center"]["body"] = shorten(slide["diagram_v5"]["center"]["body"], 26)
            for card in slide["diagram_v5"]["cards"]:
                card["body"] = compact_body_lines(card.get("body", []), 12)

        if slide.get("diagram_v5", {}).get("kind") == "mechanism-panels-clean":
            if "text-image-overlap" in issue_types or "clipping-risk" in issue_types:
                slide["diagram_v5"]["bridge_text"] = shorten(slide["diagram_v5"]["bridge_text"], 20)
                slide["bullets"] = [shorten(item, 26) for item in slide.get("bullets", [])[:2]]

    repaired["visual_qa"] = {"last_repair": "applied"}
    return repaired


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply conservative deck-spec repairs from a visual audit report.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--audit-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    audit = read_json(Path(args.audit_file))
    write_json(Path(args.output_file), apply_repairs(spec, audit))


if __name__ == "__main__":
    main()
