from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from PIL import Image

from common_io import ensure_parent, write_json, write_text

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
EMU_PER_INCH = 914400


def parse_slide_size(zf: zipfile.ZipFile) -> dict[str, float]:
    root = ET.fromstring(zf.read("ppt/presentation.xml"))
    sld_sz = root.find("p:sldSz", NS)
    if sld_sz is None:
        raise ValueError("Missing slide size in presentation.xml")
    cx = int(sld_sz.attrib["cx"])
    cy = int(sld_sz.attrib["cy"])
    return {
        "emu": {"cx": cx, "cy": cy},
        "inches": {"width": round(cx / EMU_PER_INCH, 3), "height": round(cy / EMU_PER_INCH, 3)},
    }


def parse_theme(zf: zipfile.ZipFile) -> dict[str, Any]:
    root = ET.fromstring(zf.read("ppt/theme/theme1.xml"))
    clr_scheme = root.find(".//a:clrScheme", NS)
    font_scheme = root.find(".//a:fontScheme", NS)
    colors: dict[str, str] = {}
    if clr_scheme is not None:
        for child in clr_scheme:
            name = child.tag.rsplit("}", 1)[-1]
            srgb = child.find("a:srgbClr", NS)
            sys_clr = child.find("a:sysClr", NS)
            if srgb is not None:
                colors[name] = srgb.attrib.get("val", "")
            elif sys_clr is not None:
                colors[name] = sys_clr.attrib.get("lastClr", "")
    fonts = {
        "title": "Microsoft YaHei",
        "body": "Microsoft YaHei",
    }
    if font_scheme is not None:
        major = font_scheme.find("a:majorFont/a:ea", NS)
        minor = font_scheme.find("a:minorFont/a:ea", NS)
        if major is not None and major.attrib.get("typeface"):
            fonts["title"] = major.attrib["typeface"]
        if minor is not None and minor.attrib.get("typeface"):
            fonts["body"] = minor.attrib["typeface"]
    for key, value in list(fonts.items()):
        if not value or any(ord(ch) > 127 for ch in value):
            fonts[key] = "Microsoft YaHei"
    return {"colors": colors, "fonts": fonts}


def extract_slide_texts(zf: zipfile.ZipFile) -> list[dict[str, Any]]:
    slides = sorted(
        [name for name in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name)],
        key=lambda item: int(re.search(r"(\d+)", Path(item).stem).group(1)),
    )
    items: list[dict[str, Any]] = []
    for slide_name in slides:
        slide_number = int(re.search(r"(\d+)", Path(slide_name).stem).group(1))
        root = ET.fromstring(zf.read(slide_name))
        texts = []
        for node in root.findall(".//a:t", NS):
            value = "".join(node.itertext()).strip()
            if value:
                texts.append(value)
        items.append(
            {
                "slide_number": slide_number,
                "title": texts[0] if texts else "",
                "texts": texts,
            }
        )
    return items


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def choose_representatives(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role_rules = [
        ("agenda", ["content", "目录"], 6),
        ("background-text", ["研究背景"], 10),
        ("overall-design", ["研究目标与内容", "研究目标"], 16),
        ("evidence-results", ["研究成果", "分析结果"], 31),
        ("conclusion-highlight", ["研究总结", "研究结论"], 38),
        ("route-board", ["核心论点内容", "智能图形"], 48),
        ("split-text-figure", ["两部式排版"], 50),
        ("three-part-cards", ["三部式排版"], 51),
        ("content-card-grid", ["请输入正文内容"], 52),
    ]
    selected: list[dict[str, Any]] = []
    used_numbers: set[int] = set()
    for role, keywords, fallback in role_rules:
        match = None
        for slide in slides:
            title_text = normalize_text(slide["title"])
            if any(normalize_text(keyword) in title_text for keyword in keywords):
                match = slide
                break
        if match is None:
            for slide in slides:
                text = normalize_text(" ".join(slide["texts"][:8]))
                if any(normalize_text(keyword) in text for keyword in keywords):
                    match = slide
                    break
        if match is None:
            match = next((slide for slide in slides if slide["slide_number"] == fallback), None)
        if match is None or match["slide_number"] in used_numbers:
            continue
        used_numbers.add(match["slide_number"])
        selected.append(
            {
                "role": role,
                "slide_number": match["slide_number"],
                "title": match["title"],
            }
        )
    return selected


def safe_zones() -> dict[str, Any]:
    return {
        "title_band": {"x": 0.05, "y": 0.03, "w": 0.72, "h": 0.11},
        "logo_zone": {"x": 0.80, "y": 0.02, "w": 0.17, "h": 0.11},
        "content_body": {"x": 0.05, "y": 0.14, "w": 0.90, "h": 0.76},
        "footer_band": {"x": 0.04, "y": 0.90, "w": 0.92, "h": 0.06},
        "outer_margin": 0.04,
    }


def build_brand(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "id": "neutral",
        "name_zh": args.brand_name_zh,
        "name_en": args.brand_name_en,
        "logo_file": str(Path(args.brand_logo_file).resolve()) if args.brand_logo_file else "",
        "overlay_mode": "none",
        "erase_logo_zone_in_references": True,
    }


def template_style_brief(profile: dict[str, Any]) -> str:
    colors = profile["theme"]["colors"]
    return "\n".join(
        [
            "# Academic Defense Template Style Brief",
            "",
            "- Tone: clean academic defense deck, restrained university style, bright white canvas.",
            f"- Primary accent: `#{colors.get('accent1', '2E75B5')}` academic blue, with lighter blue ladder accents for hierarchy.",
            f"- Secondary warm accent: `#{colors.get('accent6', 'B56E2E')}` only for sparse emphasis, never as the dominant page color.",
            "- Typography: Microsoft YaHei style, bold blue headings, black or dark gray body copy, frequent bilingual subheads.",
            "- Chrome: top-left heading system, a visually quiet top-right corner, generous white breathing room, thin bottom rule on some section pages.",
            "- Layout behavior: large title band, disciplined safe zones, modular cards, split text-plus-figure pages, and clean outline/summary pages.",
            "- Figure pages should still look like a disciplined university slide, not like a poster pasted onto a blank canvas.",
            "- Technical route pages must feel ordered, grid-aware, and committee-friendly, with no free-floating arrows or uncontrolled clusters.",
            "- Never render any university names, any university logos, placeholder school branding, or watermark-like identity marks.",
            "- Keep the top-right corner visually quiet and free of logos, school names, and dense content.",
            "- Do not place content inside the top-right quiet zone, title band, or footer band.",
        ]
    )


def export_template_slides(template_pptx: Path, output_dir: Path) -> None:
    # Production profile building must not invoke PowerPoint automation.
    # If reference PNGs already exist, later steps may reuse them; otherwise
    # the profile is built from PPTX package metadata only.
    output_dir.mkdir(parents=True, exist_ok=True)


def brand_reference_image(src: Path, dst: Path, brand: dict[str, Any], zones: dict[str, Any]) -> None:
    with Image.open(src) as image:
        canvas = image.convert("RGBA")
        width, height = canvas.size
        logo_zone = zones["logo_zone"]
        x = int(width * logo_zone["x"])
        y = int(height * logo_zone["y"])
        w = int(width * logo_zone["w"])
        h = int(height * logo_zone["h"])

        white = Image.new("RGBA", (w, h), (255, 255, 255, 255))
        canvas.paste(white, (x, y))

        ensure_parent(dst)
        canvas.convert("RGB").save(dst)


def copy_reference_images(export_dir: Path, selected: list[dict[str, Any]], refs_dir: Path, brand: dict[str, Any], zones: dict[str, Any]) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for item in selected:
        src = export_dir / f"slide-{item['slide_number']:03d}.png"
        if not src.exists():
            continue
        dst = refs_dir / f"{item['role']}-slide-{item['slide_number']:03d}.png"
        if brand.get("erase_logo_zone_in_references"):
            brand_reference_image(src, dst, brand, zones)
        else:
            ensure_parent(dst)
            shutil.copyfile(src, dst)
        copied.append(
            {
                **item,
                "image_file": str(dst.resolve()),
            }
        )
    return copied


def build_profile(template_pptx: Path, export_dir: Path, brand: dict[str, Any]) -> dict[str, Any]:
    with zipfile.ZipFile(template_pptx) as zf:
        slide_size = parse_slide_size(zf)
        theme = parse_theme(zf)
        slides = extract_slide_texts(zf)
    selected = choose_representatives(slides)
    zones = safe_zones()
    profile = {
        "template_id": "cdutcm-defense",
        "source_pptx": str(template_pptx.resolve()),
        "slide_count": len(slides),
        "slide_size": slide_size,
        "theme": theme,
        "safe_zones": zones,
        "brand": brand,
        "chrome_rules": {
            "title_alignment": "top-left",
            "logo_alignment": "none",
            "background": "white-first",
            "style_mode": "quiet-academic-blue",
        },
        "common_layouts": [
            "agenda",
            "background-text",
            "split-text-figure",
            "two-block-stack",
            "three-card-grid",
            "section-highlight",
            "result-summary",
        ],
        "slide_text_index": [
            {
                "slide_number": item["slide_number"],
                "title": item["title"],
            }
            for item in slides
        ],
        "selected_references": selected,
        "exports_dir": str(export_dir.resolve()),
    }
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract an academic template profile from a PPTX template without rendering a PPT/PPTX deck.")
    parser.add_argument("--template-pptx", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--output-profile-file")
    parser.add_argument("--output-brief-file")
    parser.add_argument("--brand-name-zh", default="")
    parser.add_argument("--brand-name-en", default="")
    parser.add_argument("--brand-logo-file", default="")
    args = parser.parse_args()

    template_pptx = Path(args.template_pptx).resolve()
    work_dir = Path(args.work_dir).resolve()
    export_dir = work_dir / "exported-slides"
    refs_dir = work_dir / "template_reference_pack"
    profile_file = Path(args.output_profile_file).resolve() if args.output_profile_file else work_dir / "template_profile.json"
    brief_file = Path(args.output_brief_file).resolve() if args.output_brief_file else work_dir / "template_style_brief.md"

    export_template_slides(template_pptx, export_dir)
    brand = build_brand(args)
    profile = build_profile(template_pptx, export_dir, brand)
    profile["selected_references"] = copy_reference_images(export_dir, profile["selected_references"], refs_dir, brand, profile["safe_zones"])

    write_json(profile_file, profile)
    write_text(brief_file, template_style_brief(profile))


if __name__ == "__main__":
    main()
