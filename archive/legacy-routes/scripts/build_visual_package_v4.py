from __future__ import annotations

import argparse
import copy
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance

from common_io import ensure_parent, read_json, write_json


def generate_image(
    config_file: Path,
    prompt: str,
    output_file: Path,
    request_dump: Path,
    response_dump: Path,
) -> None:
    ensure_parent(output_file)
    cmd = [
        sys.executable,
        str(Path(__file__).with_name("generate_third_party_image.py")),
        "--config-file",
        str(config_file),
        "--prompt",
        prompt,
        "--output-file",
        str(output_file),
        "--request-dump-file",
        str(request_dump),
        "--response-dump-file",
        str(response_dump),
    ]
    subprocess.run(cmd, check=True)


def polish_panel(input_file: Path, output_file: Path, white_mix: float = 0.14, saturation: float = 0.9) -> None:
    image = Image.open(input_file).convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    polished = Image.blend(image, white, white_mix)
    polished = ImageEnhance.Color(polished).enhance(saturation)
    ensure_parent(output_file)
    polished.save(output_file)


def mechanism_asset_plan() -> list[dict[str, Any]]:
    return [
        {
            "asset_id": "mechanism-infection-panel",
            "label": "感染触发",
            "prompt": (
                "Scientific journal style biological illustration, no text, no letters, no labels. "
                "Show severe bacterial lung infection in an alveolus, dense bacteria, inflammatory cells, "
                "damaged epithelial barrier, warm salmon and muted coral palette, clean medical illustration, "
                "single panel composition, suitable for PPT."
            ),
        },
        {
            "asset_id": "mechanism-pathway-panel",
            "label": "通路失衡",
            "prompt": (
                "Scientific journal style cell-mechanism illustration, no text, no letters, no labels. "
                "Show intracellular pathway dysregulation with stressed mitochondria, impaired autophagy vesicles, "
                "inflammasome-like radial signaling, sterile blue-gray cell interior with warm organelle accents, "
                "clean graphical abstract style, single panel composition, suitable for PPT."
            ),
        },
        {
            "asset_id": "mechanism-rescue-panel",
            "label": "干预逆转",
            "prompt": (
                "Scientific journal style therapeutic rescue illustration, no text, no letters, no labels. "
                "Show calmer alveolar microenvironment after intervention, fewer bacteria, restored epithelial integrity, "
                "soft cyan and blush palette, cleaner cell state, subtle autophagy recovery cues, "
                "premium graphical abstract style, single panel composition, suitable for PPT."
            ),
        },
    ]


def build_route_diagram() -> dict[str, Any]:
    return {
        "kind": "route-horizontal",
        "badge": "TECHNICAL ROUTE",
        "summary": "从临床评价到机制验证，整套研究按照四层证据递进展开。",
        "cards": [
            {"stage": "01", "title": "临床评价", "body": ["疗效与安全性", "建立临床获益基础"]},
            {"stage": "02", "title": "通路线索", "body": ["免疫炎症指标", "蛋白组筛选方向"]},
            {"stage": "03", "title": "动物验证", "body": ["整体模型复现", "验证关键通路异常"]},
            {"stage": "04", "title": "细胞闭环", "body": ["ROS/炎症/凋亡", "补足分子机制证据"]},
        ],
    }


def build_study_diagram() -> dict[str, Any]:
    return {
        "kind": "study-stack-right",
        "badge": "CLINICAL DESIGN",
        "summary": "把对象、分组、干预和评价压缩成一眼看懂的方法结构。",
        "cards": [
            {"stage": "01", "title": "研究对象", "body": ["MDR-KP重症肺炎", "明确纳入与排除标准"]},
            {"stage": "02", "title": "分组设计", "body": ["设置对照与干预分组", "保证比较路径清晰"]},
            {"stage": "03", "title": "干预实施", "body": ["统一研究流程推进", "围绕关键节点随访"]},
            {"stage": "04", "title": "评价指标", "body": ["结局指标 + 机制指标", "服务最终主结论"]},
        ],
    }


def build_evidence_diagram() -> dict[str, Any]:
    return {
        "kind": "evidence-horizontal",
        "badge": "EVIDENCE CHAIN",
        "summary": "证据链不是堆图，而是把临床、分子、动物和细胞结果组织成同一条主线。",
        "cards": [
            {"title": "临床层", "body": ["症状改善", "预后指标向好"]},
            {"title": "分子层", "body": ["免疫炎症缓解", "差异蛋白筛选"]},
            {"title": "动物层", "body": ["关键通路异常可复现", "干预后出现逆转趋势"]},
            {"title": "细胞层", "body": ["ROS下降", "炎症与凋亡减轻"]},
        ],
    }


def build_mechanism_diagram(asset_paths: list[Path]) -> dict[str, Any]:
    labels = ["感染触发", "通路失衡", "干预逆转"]
    return {
        "kind": "mechanism-panels",
        "summary": "机制页改为“无字图像元素 + 外部箭头 + 可编辑中文标签”，避免整张长图生硬拼接。",
        "panels": [
            {"label": label, "path": str(path.resolve())}
            for label, path in zip(labels, asset_paths, strict=True)
        ],
        "bridge_text": "HQQD 介入后，自噬与炎症调控趋于恢复",
    }


def update_v4_slides(spec: dict[str, Any], mechanism_assets: list[Path]) -> dict[str, Any]:
    refined = copy.deepcopy(spec)
    for slide in refined.get("slides", []):
        slide_id = slide.get("id")
        if slide_id == "slide-09":
            slide.pop("figure", None)
            slide["layout_hint"] = "native-full"
            slide["diagram_v4"] = build_route_diagram()
            slide["takeaway"] = "技术路线页改为原生 PPT 卡片与外部箭头，不再使用带字流程图图片。"
        elif slide_id == "slide-12":
            slide.pop("figure", None)
            slide["layout_hint"] = "native-right"
            slide["diagram_v4"] = build_study_diagram()
            slide["takeaway"] = "方法页的图形说明改成原生 PPT 结构，内部字体与整页标题系统保持一致。"
        elif slide_id == "slide-31":
            slide.pop("figure", None)
            slide["layout_hint"] = "native-full"
            slide["diagram_v4"] = build_evidence_diagram()
            slide["takeaway"] = "证据链页改成横向四卡片结构，箭头放在卡片外部，逻辑更清楚。"
        elif slide_id == "slide-32":
            slide["layout_hint"] = "native-full"
            slide["diagram_v4"] = build_mechanism_diagram(mechanism_assets)
            slide["takeaway"] = "机制页不再是一整张长图，而是三个图像元素拼装后的混合机制图。"
    refined["schema_version"] = "0.7"
    refined["visual_pass"] = {
        "stage": "v4",
        "strategy": "native-ppt-diagrams-plus-mechanism-elements",
    }
    return refined


def main() -> None:
    parser = argparse.ArgumentParser(description="Build V4 review assets with native PPT diagrams and element-based mechanism panels.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--output-spec-file", required=True)
    parser.add_argument("--assets-dir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--image-config-file", required=True)
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    assets_dir = Path(args.assets_dir)
    config_file = Path(args.image_config_file)
    assets_dir.mkdir(parents=True, exist_ok=True)

    asset_paths: list[Path] = []
    plan_assets: list[dict[str, Any]] = []
    for item in mechanism_asset_plan():
        raw_path = assets_dir / f"{item['asset_id']}-raw.png"
        final_path = assets_dir / f"{item['asset_id']}.png"
        request_dump = assets_dir / f"{item['asset_id']}-request.json"
        response_dump = assets_dir / f"{item['asset_id']}-response.json"

        generate_image(config_file, item["prompt"], raw_path, request_dump, response_dump)
        polish_panel(raw_path, final_path)

        asset_paths.append(final_path)
        plan_assets.append(
            {
                "asset_id": item["asset_id"],
                "label": item["label"],
                "final_path": str(final_path.resolve()),
                "request_dump": str(request_dump.resolve()),
                "response_dump": str(response_dump.resolve()),
            }
        )

    refined = update_v4_slides(spec, asset_paths)
    write_json(Path(args.output_spec_file), refined)
    write_json(
        Path(args.plan_file),
        {
            "schema_version": "0.1",
            "stage": "v4",
            "assets": plan_assets,
            "diagram_shift": [
                "slide-09: native route cards",
                "slide-12: native study design stack",
                "slide-31: native evidence chain cards",
                "slide-32: three mechanism image elements with native labels",
            ],
        },
    )


if __name__ == "__main__":
    main()
