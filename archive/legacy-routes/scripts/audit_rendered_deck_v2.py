from __future__ import annotations

import argparse
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from common_io import read_json, write_json, write_text

EMU_PER_INCH = 914400
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


@dataclass
class Box:
    kind: str
    name: str
    text: str
    font_size: float
    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return max(self.w, 0.0) * max(self.h, 0.0)


def rect_overlap(a: Box, b: Box) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.w, b.x + b.w)
    y2 = min(a.y + a.h, b.y + b.h)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def bbox_from_xfrm(node: ET.Element, slide_w: int, slide_h: int) -> tuple[float, float, float, float] | None:
    xfrm = node.find(".//a:xfrm", NS)
    if xfrm is None:
        return None
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return None
    return (
        int(off.attrib.get("x", "0")) / slide_w,
        int(off.attrib.get("y", "0")) / slide_h,
        int(ext.attrib.get("cx", "0")) / slide_w,
        int(ext.attrib.get("cy", "0")) / slide_h,
    )


def collect_boxes(slide_xml: bytes, slide_w: int, slide_h: int) -> list[Box]:
    root = ET.fromstring(slide_xml)
    boxes: list[Box] = []

    for shape in root.findall(".//p:sp", NS):
        bbox = bbox_from_xfrm(shape, slide_w, slide_h)
        if not bbox:
            continue
        texts = [node.text or "" for node in shape.findall(".//a:t", NS)]
        text = "".join(texts).strip()
        font_sizes = []
        for font_node in shape.findall(".//a:rPr", NS) + shape.findall(".//a:defRPr", NS) + shape.findall(".//a:endParaRPr", NS):
            size = font_node.attrib.get("sz")
            if size:
                font_sizes.append(int(size) / 100)
        font_size = round(sum(font_sizes) / len(font_sizes), 2) if font_sizes else 18.0
        nv = shape.find("p:nvSpPr/p:cNvPr", NS)
        name = nv.attrib.get("name", "shape") if nv is not None else "shape"
        kind = "text" if text else "shape"
        boxes.append(Box(kind=kind, name=name, text=text, font_size=font_size, x=bbox[0], y=bbox[1], w=bbox[2], h=bbox[3]))

    for pic in root.findall(".//p:pic", NS):
        bbox = bbox_from_xfrm(pic, slide_w, slide_h)
        if not bbox:
            continue
        nv = pic.find("p:nvPicPr/p:cNvPr", NS)
        name = nv.attrib.get("name", "image") if nv is not None else "image"
        boxes.append(Box(kind="image", name=name, text="", font_size=0.0, x=bbox[0], y=bbox[1], w=bbox[2], h=bbox[3]))

    for connector in root.findall(".//p:cxnSp", NS):
        bbox = bbox_from_xfrm(connector, slide_w, slide_h)
        if not bbox:
            continue
        nv = connector.find("p:nvCxnSpPr/p:cNvPr", NS)
        name = nv.attrib.get("name", "connector") if nv is not None else "connector"
        boxes.append(Box(kind="connector", name=name, text="", font_size=0.0, x=bbox[0], y=bbox[1], w=bbox[2], h=bbox[3]))

    return boxes


def parse_slide_size(presentation_xml: bytes) -> tuple[int, int]:
    root = ET.fromstring(presentation_xml)
    sld_sz = root.find("p:sldSz", NS)
    if sld_sz is None:
        raise ValueError("Missing slide size in presentation.xml")
    return int(sld_sz.attrib["cx"]), int(sld_sz.attrib["cy"])


def is_auxiliary_text(box: Box) -> bool:
    if box.kind != "text":
        return False
    if box.y < 0.12:
        return True
    if box.y + box.h > 0.92 and box.h < 0.05:
        return True
    if "/" in box.text and len(box.text) <= 10:
        return True
    if "Academic Elegance" in box.text:
        return True
    return False


def overflow_ratio(box: Box, slide_w_pt: float, slide_h_pt: float) -> float:
    lines = max(1, box.text.count("\n") + 1)
    box_w_pt = box.w * slide_w_pt
    box_h_pt = box.h * slide_h_pt
    chars_per_line = max(1.0, box_w_pt / max(box.font_size * 0.92, 1.0))
    line_capacity = max(1.0, box_h_pt / max(box.font_size * 1.38, 1.0))
    estimated_capacity = chars_per_line * line_capacity
    weighted_length = len(box.text) + lines * 1.5
    return weighted_length / estimated_capacity if estimated_capacity else 0.0


def is_background_image_for_slide(image_box: Box, slide_spec: dict[str, Any] | None) -> bool:
    if not slide_spec:
        return False
    if slide_spec.get("visual_route") != "gemini-editable-hybrid":
        return False
    return image_box.area >= 0.18


def audit_slide(
    slide_number: int,
    boxes: list[Box],
    slide_title: str,
    slide_w_emu: int,
    slide_h_emu: int,
    slide_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    text_boxes = [box for box in boxes if box.kind == "text" and box.text]
    image_boxes = [box for box in boxes if box.kind == "image"]
    connector_boxes = [box for box in boxes if box.kind == "connector"]
    content_text_boxes = [box for box in text_boxes if not is_auxiliary_text(box)]
    slide_w_pt = slide_w_emu / EMU_PER_INCH * 72
    slide_h_pt = slide_h_emu / EMU_PER_INCH * 72

    for box in content_text_boxes:
        if box.x < 0.02 or box.y < 0.02 or box.x + box.w > 0.985 or box.y + box.h > 0.965:
            issues.append(
                {
                    "severity": "medium",
                    "type": "edge-risk",
                    "box": box.name,
                    "message": f"文本框 {box.name} 贴边，可能出现压边或裁切。",
                }
            )
        fit_ratio = overflow_ratio(box, slide_w_pt, slide_h_pt)
        if fit_ratio > 1.18:
            issues.append(
                {
                    "severity": "high",
                    "type": "clipping-risk",
                    "box": box.name,
                    "message": f"文本框 {box.name} 的文字估算容量不足，疑似发生溢出或压缩过度。",
                    "score": round(fit_ratio, 4),
                }
            )

    for idx, box in enumerate(content_text_boxes):
        for other in content_text_boxes[idx + 1 :]:
            overlap = rect_overlap(box, other)
            if overlap > min(box.area, other.area) * 0.12:
                issues.append(
                    {
                        "severity": "high",
                        "type": "text-overlap",
                        "boxes": [box.name, other.name],
                        "message": f"文本框 {box.name} 与 {other.name} 存在明显重叠。",
                    }
                )
        for image_box in image_boxes:
            if is_background_image_for_slide(image_box, slide_spec):
                continue
            overlap = rect_overlap(box, image_box)
            if overlap > box.area * 0.12:
                issues.append(
                    {
                        "severity": "high",
                        "type": "text-image-overlap",
                        "boxes": [box.name, image_box.name],
                        "message": f"文本框 {box.name} 侵入图片区域 {image_box.name}。",
                    }
                )

    for box in content_text_boxes:
        for connector_box in connector_boxes:
            overlap = rect_overlap(box, connector_box)
            if overlap > box.area * 0.02:
                issues.append(
                    {
                        "severity": "high",
                        "type": "connector-text-overlap",
                        "boxes": [box.name, connector_box.name],
                        "message": f"Connector {connector_box.name} overlaps text box {box.name}.",
                    }
                )

    text_area = sum(box.area for box in content_text_boxes)
    if text_area > 0.38:
        issues.append(
            {
                "severity": "medium",
                "type": "density-high",
                "message": "整页文字面积偏高，可能出现拥挤或视觉喘不过气。",
                "score": round(text_area, 4),
            }
        )

    return {
        "slide_number": slide_number,
        "slide_title": slide_title,
        "text_box_count": len(content_text_boxes),
        "image_box_count": len(image_boxes),
        "connector_count": len(connector_boxes),
        "issue_count": len(issues),
        "issues": issues,
        "status": "fail" if any(issue["severity"] == "high" for issue in issues) else ("warn" if issues else "pass"),
    }


def title_lookup(spec: dict[str, Any]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for idx, slide in enumerate(spec.get("slides", []), start=1):
        mapping[idx] = slide.get("title", f"slide-{idx:02d}")
    return mapping


def slide_lookup(spec: dict[str, Any]) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for idx, slide in enumerate(spec.get("slides", []), start=1):
        mapping[idx] = slide
    return mapping


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Visual QA Report",
        "",
        f"- 审核页数：{report['summary']['slides']}",
        f"- 通过：{report['summary']['pass']}",
        f"- 警告：{report['summary']['warn']}",
        f"- 失败：{report['summary']['fail']}",
        "",
        "## Findings",
    ]
    for slide in report["slides"]:
        if not slide["issues"]:
            continue
        lines.append(f"### Slide {slide['slide_number']} - {slide['slide_title']}")
        for issue in slide["issues"]:
            lines.append(f"- `{issue['severity']}` `{issue['type']}` {issue['message']}")
        lines.append("")
    if all(not slide["issues"] for slide in report["slides"]):
        lines.append("- 未发现明显重叠、压边或拥挤问题。")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit rendered PPT slide geometry for crowding, clipping, and overlap risks.")
    parser.add_argument("--pptx-file", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--spec-file")
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file)) if args.spec_file else {"slides": []}
    title_map = title_lookup(spec)
    slide_map = slide_lookup(spec)

    with zipfile.ZipFile(args.pptx_file) as zf:
        slide_w, slide_h = parse_slide_size(zf.read("ppt/presentation.xml"))
        slide_files = sorted(
            [name for name in zf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")],
            key=lambda item: int(Path(item).stem.replace("slide", "")),
        )
        slide_reports: list[dict[str, Any]] = []
        for slide_file in slide_files:
            slide_number = int(Path(slide_file).stem.replace("slide", ""))
            boxes = collect_boxes(zf.read(slide_file), slide_w, slide_h)
            slide_reports.append(
                audit_slide(
                    slide_number=slide_number,
                    boxes=boxes,
                    slide_title=title_map.get(slide_number, f"slide-{slide_number:02d}"),
                    slide_w_emu=slide_w,
                    slide_h_emu=slide_h,
                    slide_spec=slide_map.get(slide_number),
                )
            )

    summary = {
        "slides": len(slide_reports),
        "pass": sum(1 for item in slide_reports if item["status"] == "pass"),
        "warn": sum(1 for item in slide_reports if item["status"] == "warn"),
        "fail": sum(1 for item in slide_reports if item["status"] == "fail"),
    }
    report = {"summary": summary, "slides": slide_reports}
    write_json(Path(args.output_json), report)
    write_text(Path(args.output_md), report_markdown(report))


if __name__ == "__main__":
    main()
