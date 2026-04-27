from __future__ import annotations

import argparse
import copy
import html
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from common_io import read_json, write_json, write_text

CARD_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF8F2;strokeColor=#A36A54;"
    "fontColor=#223046;arcSize=16;strokeWidth=1.5;"
)
LIGHT_CARD_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#D8C7B8;"
    "fontColor=#223046;arcSize=16;strokeWidth=1.2;"
)
CHIP_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#1F2E3D;strokeColor=#1F2E3D;"
    "fontColor=#FFFFFF;arcSize=24;strokeWidth=1;"
)
PALE_CHIP_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#F6EEE6;strokeColor=#F6EEE6;"
    "fontColor=#A36A54;arcSize=24;strokeWidth=1;fontStyle=1;"
)
TEXT_STYLE = (
    "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontColor=#364152;"
    "fontSize=12;"
)
EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=1;jettySize=auto;strokeColor=#A36A54;"
    "strokeWidth=1.6;endArrow=block;endFill=1;"
)
LINE_STYLE = "strokeColor=#C9B09E;strokeWidth=1.4;"
EXPORT_EXT_PRIORITY = {
    ".png": 0,
    ".svg": 1,
    ".jpg": 2,
    ".jpeg": 3,
}
EXPORT_NAME_HINTS = ["exported", "final", "diagram", "board", "slide", "preview", "draft"]


def safe_stem(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower() or "slide"


def clean_line(value: str) -> str:
    return " ".join(str(value or "").split())


def truncate(value: str, limit: int = 34) -> str:
    text = clean_line(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def split_brief(value: str, limit: int = 18) -> list[str]:
    text = clean_line(value)
    if not text:
        return []
    chunks = re.split(r"[；;。,.，、]", text)
    prepared = [truncate(chunk, limit) for chunk in chunks if clean_line(chunk)]
    if prepared:
        return prepared[:2]
    midpoint = max(1, len(text) // 2)
    return [truncate(text[:midpoint], limit), truncate(text[midpoint:], limit)]


def html_label(title: str, lines: list[str]) -> str:
    title_text = html.escape(truncate(title, 24))
    body = "<br/>".join(html.escape(truncate(line, 28)) for line in lines if clean_line(line))
    if body:
        return f"<b>{title_text}</b><br/>{body}"
    return f"<b>{title_text}</b>"


def chunked(items: list[str], target: int) -> list[list[str]]:
    if not items:
        return [[] for _ in range(target)]
    groups: list[list[str]] = [[] for _ in range(target)]
    for index, item in enumerate(items):
        groups[index % target].append(item)
    return groups


def find_exported_assets(slide_dir: Path) -> list[dict[str, str]]:
    candidates: list[tuple[int, int, int, Path]] = []
    for path in slide_dir.iterdir():
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in EXPORT_EXT_PRIORITY:
            continue
        stem = path.stem.lower()
        name_rank = next((index for index, token in enumerate(EXPORT_NAME_HINTS) if token in stem), len(EXPORT_NAME_HINTS))
        candidates.append((EXPORT_EXT_PRIORITY[suffix], name_rank, len(path.name), path))

    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3].name.lower()))
    return [
        {
            "path": str(path.resolve()),
            "format": path.suffix.lower().lstrip("."),
            "file_name": path.name,
        }
        for _, _, _, path in candidates
    ]


class DrawioXml:
    def __init__(self, width: int = 1400, height: int = 900) -> None:
        self.graph = ET.Element(
            "mxGraphModel",
            {
                "dx": "1422",
                "dy": "794",
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "pageWidth": str(width),
                "pageHeight": str(height),
                "math": "0",
                "shadow": "0",
                "background": "#FFFDF9",
                "adaptiveColors": "auto",
            },
        )
        self.root = ET.SubElement(self.graph, "root")
        ET.SubElement(self.root, "mxCell", {"id": "0"})
        ET.SubElement(self.root, "mxCell", {"id": "1", "parent": "0"})
        self.next_id = 2

    def _new_id(self) -> str:
        current = str(self.next_id)
        self.next_id += 1
        return current

    def add_vertex(self, value: str, x: int, y: int, width: int, height: int, style: str, parent: str = "1") -> str:
        cell_id = self._new_id()
        cell = ET.SubElement(
            self.root,
            "mxCell",
            {
                "id": cell_id,
                "value": value,
                "style": style,
                "vertex": "1",
                "parent": parent,
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "as": "geometry",
            },
        )
        return cell_id

    def add_edge(
        self,
        source: str,
        target: str,
        style: str = EDGE_STYLE,
        value: str = "",
        points: list[tuple[int, int]] | None = None,
    ) -> str:
        cell_id = self._new_id()
        cell = ET.SubElement(
            self.root,
            "mxCell",
            {
                "id": cell_id,
                "value": value,
                "style": style,
                "edge": "1",
                "source": source,
                "target": target,
                "parent": "1",
            },
        )
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if points:
            array = ET.SubElement(geometry, "Array", {"as": "points"})
            for x, y in points:
                ET.SubElement(array, "mxPoint", {"x": str(x), "y": str(y)})
        return cell_id

    def to_string(self) -> str:
        ET.indent(self.graph, space="  ")
        return ET.tostring(self.graph, encoding="unicode")


def infer_board_kind(slide: dict[str, Any]) -> str | None:
    diagram_kind = slide.get("diagram_v5", {}).get("kind")
    if diagram_kind in {"route-board", "study-board", "evidence-board"}:
        return diagram_kind
    visual_type = slide.get("visual_type")
    if visual_type == "process-flow":
        return "route-board"
    if visual_type == "study-design":
        return "study-board"
    if visual_type == "evidence-chain":
        return "evidence-board"

    title = str(slide.get("title", ""))
    if "技术路线" in title:
        return "route-board"
    if "设计" in title and "对象" in title:
        return "study-board"
    if "证据链" in title:
        return "evidence-board"
    return None


def extract_route_payload(slide: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(slide.get("diagram_v5", {}))
    if payload.get("kind") == "route-board":
        return payload

    bullets = [clean_line(item) for item in slide.get("bullets", []) if clean_line(item)]
    stages = ["临床入口", "分子线索", "动物验证", "细胞闭环"]
    cards = []
    for index, title in enumerate(stages):
        source = bullets[index] if index < len(bullets) else slide.get("takeaway", "")
        cards.append(
            {
                "stage": f"{index + 1:02d}",
                "title": title,
                "body": split_brief(source, 16) or [truncate(source, 18)],
            }
        )

    return {
        "kind": "route-board",
        "badge": "TECHNICAL ROUTE",
        "summary": truncate(slide.get("takeaway") or "将整篇论文的临床、分子、动物与细胞证据压缩成一张可编辑路线图。", 56),
        "goal_chips": [card["title"] for card in cards],
        "center": {
            "title": "核心问题",
            "body": truncate(slide.get("title", "论文研究主线"), 44),
        },
        "left_rail": {"title": "起点", "items": split_brief(bullets[0], 16) if bullets else ["临床问题提出"]},
        "right_rail": {"title": "落点", "items": split_brief(slide.get("takeaway", ""), 16) or ["形成主结论"]},
        "cards": cards,
        "outputs": split_brief(slide.get("takeaway", ""), 16) or ["支撑主结论", "服务答辩主线"],
    }


def extract_study_payload(slide: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(slide.get("diagram_v5", {}))
    if payload.get("kind") == "study-board":
        return payload

    bullets = [clean_line(item) for item in slide.get("bullets", []) if clean_line(item)]
    titles = ["研究对象", "分组设计", "干预与检测", "结局关注"]
    grouped = chunked(bullets[:4] or [slide.get("takeaway", "")], 4)
    cards = []
    for index, title in enumerate(titles):
        lines = [truncate(item, 22) for item in grouped[index] if clean_line(item)]
        if not lines:
            fallback = slide.get("takeaway", "") if index == 3 else slide.get("title", "")
            lines = split_brief(fallback, 18) or [truncate(fallback, 18)]
        cards.append({"stage": f"{index + 1:02d}", "title": title, "body": lines[:2]})

    return {
        "kind": "study-board",
        "badge": "STUDY DESIGN",
        "summary": truncate(slide.get("takeaway") or "把对象、分组、干预和结局压缩成一眼看懂的研究设计结构。", 56),
        "cards": cards,
        "bottom_chips": ["对象清晰", "分组明确", "流程闭环", "评价聚焦"],
    }


def extract_evidence_payload(slide: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(slide.get("diagram_v5", {}))
    if payload.get("kind") == "evidence-board":
        return payload

    bullets = [clean_line(item) for item in slide.get("bullets", []) if clean_line(item)]
    titles = ["临床层", "分子层", "动物层", "细胞层"]
    grouped = chunked(bullets[:4] or [slide.get("takeaway", "")], 4)
    cards = []
    for index, title in enumerate(titles):
        lines = [truncate(item, 20) for item in grouped[index] if clean_line(item)]
        if not lines:
            lines = [truncate(slide.get("takeaway", ""), 20)]
        cards.append({"title": title, "body": lines[:2]})

    return {
        "kind": "evidence-board",
        "badge": "EVIDENCE CHAIN",
        "summary": truncate(slide.get("takeaway") or "把四层证据组织成围绕主结论的证据看板。", 56),
        "cards": cards,
        "center": {
            "title": "主结论",
            "body": truncate(slide.get("takeaway", slide.get("title", "主结论")), 42),
        },
    }


def build_route_mermaid(payload: dict[str, Any]) -> str:
    lines = [
        "flowchart LR",
        "    classDef main fill:#FFF8F2,stroke:#A36A54,stroke-width:1.5px,color:#223046;",
        "    classDef chip fill:#1F2E3D,stroke:#1F2E3D,color:#FFFFFF;",
        f'    Q["{html.escape(payload["center"]["title"])}<br/>{html.escape(payload["center"]["body"])}"]:::main',
        f'    L["{html.escape(payload["left_rail"]["title"])}<br/>' + "<br/>".join(html.escape(item) for item in payload["left_rail"]["items"]) + '"]:::chip',
        f'    R["{html.escape(payload["right_rail"]["title"])}<br/>' + "<br/>".join(html.escape(item) for item in payload["right_rail"]["items"]) + '"]:::chip',
    ]

    card_ids = []
    for index, card in enumerate(payload["cards"], start=1):
        card_id = f"C{index}"
        card_ids.append(card_id)
        body = "<br/>".join(html.escape(item) for item in card["body"])
        lines.append(f'    {card_id}["{html.escape(card["stage"])} {html.escape(card["title"])}<br/>{body}"]:::main')

    lines.append(f"    L --> {card_ids[0]}")
    for source, target in zip(card_ids, card_ids[1:]):
        lines.append(f"    {source} --> {target}")
    lines.append(f"    {card_ids[-1]} --> R")
    lines.append(f"    Q -.研究主线.-> {card_ids[1] if len(card_ids) > 1 else card_ids[0]}")
    return "\n".join(lines) + "\n"


def build_study_mermaid(payload: dict[str, Any]) -> str:
    lines = [
        "flowchart TD",
        "    classDef main fill:#FFF8F2,stroke:#A36A54,stroke-width:1.5px,color:#223046;",
    ]
    previous = None
    for index, card in enumerate(payload["cards"], start=1):
        node_id = f"S{index}"
        body = "<br/>".join(html.escape(item) for item in card["body"])
        lines.append(f'    {node_id}["{html.escape(card["stage"])} {html.escape(card["title"])}<br/>{body}"]:::main')
        if previous:
            lines.append(f"    {previous} --> {node_id}")
        previous = node_id
    return "\n".join(lines) + "\n"


def build_evidence_mermaid(payload: dict[str, Any]) -> str:
    lines = [
        "flowchart TB",
        "    classDef main fill:#FFF8F2,stroke:#A36A54,stroke-width:1.5px,color:#223046;",
        "    classDef center fill:#1F2E3D,stroke:#1F2E3D,color:#FFFFFF;",
        f'    C["{html.escape(payload["center"]["title"])}<br/>{html.escape(payload["center"]["body"])}"]:::center',
    ]
    for index, card in enumerate(payload["cards"], start=1):
        node_id = f"E{index}"
        body = "<br/>".join(html.escape(item) for item in card["body"])
        lines.append(f'    {node_id}["{html.escape(card["title"])}<br/>{body}"]:::main')
        lines.append(f"    {node_id} --> C")
    return "\n".join(lines) + "\n"


def build_route_xml(payload: dict[str, Any]) -> str:
    diagram = DrawioXml(width=1600, height=960)
    diagram.add_vertex(payload["badge"], 50, 34, 190, 38, PALE_CHIP_STYLE)
    diagram.add_vertex(payload["summary"], 50, 82, 1430, 48, TEXT_STYLE)

    left = diagram.add_vertex(
        html_label(payload["left_rail"]["title"], payload["left_rail"]["items"]),
        50,
        150,
        230,
        240,
        LIGHT_CARD_STYLE,
    )
    center = diagram.add_vertex(
        html_label(payload["center"]["title"], split_brief(payload["center"]["body"], 24)),
        560,
        146,
        480,
        126,
        CARD_STYLE,
    )
    right = diagram.add_vertex(
        html_label(payload["right_rail"]["title"], payload["right_rail"]["items"]),
        1320,
        150,
        230,
        240,
        LIGHT_CARD_STYLE,
    )

    card_ids: list[str] = []
    x_positions = [90, 455, 820, 1185]
    for index, card in enumerate(payload["cards"]):
        card_ids.append(
            diagram.add_vertex(
                html_label(f'{card["stage"]} {card["title"]}', card["body"]),
                x_positions[index],
                430,
                280,
                132,
                CARD_STYLE,
            )
        )

    diagram.add_edge(left, card_ids[0], points=[(180, 430), (230, 430)])
    diagram.add_edge(center, card_ids[1], points=[(800, 320), (800, 430)])
    for source, target in zip(card_ids, card_ids[1:]):
        diagram.add_edge(source, target)
    diagram.add_edge(card_ids[-1], right, points=[(1460, 496), (1460, 390)])

    output_box = diagram.add_vertex(
        html_label("输出落点", payload["outputs"]),
        300,
        700,
        1000,
        120,
        LIGHT_CARD_STYLE,
    )
    diagram.add_edge(card_ids[1], output_box, points=[(595, 630), (595, 700)])
    diagram.add_edge(card_ids[2], output_box, points=[(960, 630), (960, 700)])
    return diagram.to_string()


def build_study_xml(payload: dict[str, Any]) -> str:
    diagram = DrawioXml(width=1500, height=960)
    diagram.add_vertex(payload["badge"], 90, 42, 220, 40, PALE_CHIP_STYLE)
    diagram.add_vertex(payload["summary"], 90, 95, 1300, 48, TEXT_STYLE)
    diagram.add_vertex("", 150, 180, 2, 580, LINE_STYLE)

    y_positions = [160, 315, 470, 625]
    card_ids: list[str] = []
    for index, card in enumerate(payload["cards"]):
        stage_id = diagram.add_vertex(card["stage"], 115, y_positions[index] + 42, 56, 40, CHIP_STYLE)
        card_id = diagram.add_vertex("", 220, y_positions[index], 1120, 120, LIGHT_CARD_STYLE)
        card_ids.append(card_id)
        diagram.add_vertex(card["title"], 248, y_positions[index] + 18, 280, 34, PALE_CHIP_STYLE)
        diagram.add_vertex("<br/>".join(html.escape(item) for item in card["body"]), 252, y_positions[index] + 64, 960, 38, TEXT_STYLE)
        if index > 0:
            diagram.add_edge(stage_id, card_ids[index], points=[(170, y_positions[index] + 62), (220, y_positions[index] + 62)])

    chip_x = 250
    for item in payload.get("bottom_chips", []):
        width = max(120, min(220, 24 + len(clean_line(item)) * 18))
        diagram.add_vertex(item, chip_x, 808, width, 36, PALE_CHIP_STYLE)
        chip_x += width + 18

    return diagram.to_string()


def build_evidence_xml(payload: dict[str, Any]) -> str:
    diagram = DrawioXml(width=1500, height=960)
    diagram.add_vertex(payload["badge"], 90, 44, 220, 40, PALE_CHIP_STYLE)
    diagram.add_vertex(payload["summary"], 90, 98, 1300, 48, TEXT_STYLE)

    center = diagram.add_vertex(
        html_label(payload["center"]["title"], split_brief(payload["center"]["body"], 20)),
        560,
        360,
        380,
        122,
        CHIP_STYLE,
    )

    positions = [
        (120, 170),
        (1000, 170),
        (120, 590),
        (1000, 590),
    ]
    for card, (x, y) in zip(payload["cards"], positions):
        node = diagram.add_vertex(html_label(card["title"], card["body"]), x, y, 350, 128, CARD_STYLE)
        diagram.add_edge(node, center)

    return diagram.to_string()


def build_mermaid(slide: dict[str, Any], board_kind: str) -> str:
    if board_kind == "route-board":
        return build_route_mermaid(extract_route_payload(slide))
    if board_kind == "study-board":
        return build_study_mermaid(extract_study_payload(slide))
    return build_evidence_mermaid(extract_evidence_payload(slide))


def build_xml(slide: dict[str, Any], board_kind: str) -> str:
    if board_kind == "route-board":
        return build_route_xml(extract_route_payload(slide))
    if board_kind == "study-board":
        return build_study_xml(extract_study_payload(slide))
    return build_evidence_xml(extract_evidence_payload(slide))


def select_slide_ids(spec: dict[str, Any], audit: dict[str, Any] | None, only_failed: bool, requested_ids: set[str] | None) -> set[str]:
    if requested_ids:
        return requested_ids

    selected: set[str] = set()
    issues_by_number = {}
    if audit:
        for item in audit.get("slides", []):
            issues_by_number[item["slide_number"]] = item

    for slide_number, slide in enumerate(spec.get("slides", []), start=1):
        board_kind = infer_board_kind(slide)
        if not board_kind:
            continue
        if not audit:
            selected.add(slide["id"])
            continue

        audit_slide = issues_by_number.get(slide_number)
        if not audit_slide:
            continue
        if only_failed:
            if audit_slide.get("status") == "fail":
                selected.add(slide["id"])
            continue

        issue_types = {issue["type"] for issue in audit_slide.get("issues", [])}
        if audit_slide.get("status") in {"fail", "warn"} or issue_types & {"text-overlap", "text-image-overlap", "clipping-risk"}:
            selected.add(slide["id"])

    return selected


def enrich_spec(spec: dict[str, Any], manifest_entries: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = copy.deepcopy(spec)
    entries_by_slide = {entry["slide_id"]: entry for entry in manifest_entries}
    for slide in enriched.get("slides", []):
        entry = entries_by_slide.get(slide.get("id"))
        if not entry:
            continue
        slide["drawio_backend"] = {
            "route": "drawio-mcp-diagram-lab",
            "status": "exported" if entry.get("exported_asset") else "drafted",
            "board_kind": entry["board_kind"],
            "preferred_tool": entry["preferred_tool"],
            "artifact_dir": entry["artifact_dir"],
            "xml_file": entry["xml_file"],
            "mermaid_file": entry["mermaid_file"],
            "issues": entry["issues"],
        }
        if entry.get("exported_assets"):
            slide["drawio_backend"]["exported_assets"] = entry["exported_assets"]
        if entry.get("exported_asset"):
            slide["drawio_backend"]["exported_asset"] = entry["exported_asset"]
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(description="Build draw.io MCP draft artifacts for complex thesis slides.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--audit-file")
    parser.add_argument("--only-failed", action="store_true")
    parser.add_argument("--slide-ids", help="Comma-separated slide ids to force-build.")
    parser.add_argument("--output-spec-file")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    spec = read_json(Path(args.spec_file))
    audit = read_json(Path(args.audit_file)) if args.audit_file else None
    output_dir = Path(args.output_dir)
    requested_ids = {item.strip() for item in (args.slide_ids or "").split(",") if item.strip()} or None
    selected_ids = select_slide_ids(spec, audit, args.only_failed, requested_ids)

    issues_by_number = {
        item["slide_number"]: item
        for item in (audit or {}).get("slides", [])
    }

    manifest_entries: list[dict[str, Any]] = []
    drawio_client = root / "scripts" / "drawio_mcp_client.mjs"

    for slide_number, slide in enumerate(spec.get("slides", []), start=1):
        slide_id = slide.get("id")
        if slide_id not in selected_ids:
            continue

        board_kind = infer_board_kind(slide)
        if not board_kind:
            continue

        slide_dir = output_dir / safe_stem(slide_id)
        xml_file = slide_dir / "draft.xml"
        mermaid_file = slide_dir / "draft.mmd"
        context_file = slide_dir / "context.json"
        response_file = slide_dir / "open-xml-response.json"
        audit_item = issues_by_number.get(slide_number, {})

        mermaid = build_mermaid(slide, board_kind)
        xml_text = build_xml(slide, board_kind)
        write_text(mermaid_file, mermaid)
        write_text(xml_file, xml_text)
        exported_assets = find_exported_assets(slide_dir)
        exported_asset = exported_assets[0] if exported_assets else None

        context = {
            "slide_id": slide_id,
            "slide_number": slide_number,
            "title": slide.get("title"),
            "visual_type": slide.get("visual_type"),
            "board_kind": board_kind,
            "preferred_tool": "open_drawio_xml",
            "issues": audit_item.get("issues", []),
            "notes": slide.get("notes"),
            "takeaway": slide.get("takeaway"),
            "files": {
                "xml_file": str(xml_file.resolve()),
                "mermaid_file": str(mermaid_file.resolve()),
            },
            "exported_assets": exported_assets,
            "open_commands": {
                "xml": f'node "{drawio_client.resolve()}" open-xml --content-file "{xml_file.resolve()}" --response-file "{response_file.resolve()}"',
                "mermaid": f'node "{drawio_client.resolve()}" open-mermaid --content-file "{mermaid_file.resolve()}"',
            },
        }
        write_json(context_file, context)

        manifest_entries.append(
            {
                "slide_id": slide_id,
                "slide_number": slide_number,
                "title": slide.get("title"),
                "visual_type": slide.get("visual_type"),
                "board_kind": board_kind,
                "preferred_tool": "open_drawio_xml",
                "artifact_dir": str(slide_dir.resolve()),
                "xml_file": str(xml_file.resolve()),
                "mermaid_file": str(mermaid_file.resolve()),
                "context_file": str(context_file.resolve()),
                "issues": audit_item.get("issues", []),
                "exported_assets": exported_assets,
                "exported_asset": exported_asset,
            }
        )

    manifest = {
        "schema_version": "0.1",
        "spec_file": str(Path(args.spec_file).resolve()),
        "audit_file": str(Path(args.audit_file).resolve()) if args.audit_file else None,
        "selected_slide_ids": sorted(selected_ids),
        "entries": manifest_entries,
    }
    write_json(output_dir / "drawio-manifest.json", manifest)

    if args.output_spec_file:
        write_json(Path(args.output_spec_file), enrich_spec(spec, manifest_entries))


if __name__ == "__main__":
    main()
