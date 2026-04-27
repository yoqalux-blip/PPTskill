from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

from common_io import read_json, write_json


def build_route_board() -> dict[str, Any]:
    return {
        "kind": "route-board",
        "badge": "TECHNICAL ROUTE",
        "summary": "参考高密度技术路线图，把研究目标、四级证据主线和最终落点压缩到同一张路线看板中。",
        "goal_chips": ["临床获益", "通路线索", "动物验证", "细胞闭环"],
        "center": {
            "title": "核心问题",
            "body": "HQQD 是否改善 MDR-KP 重症肺炎，并通过自噬与炎症调控发挥保护作用",
        },
        "left_rail": {
            "title": "临床入口",
            "items": ["症状改善", "预后向好", "安全性可接受"],
        },
        "right_rail": {
            "title": "机制闭环",
            "items": ["蛋白组筛选", "动物复现", "细胞验证"],
        },
        "cards": [
            {"stage": "01", "title": "临床评价", "body": ["疗效与安全性", "建立临床获益基础"]},
            {"stage": "02", "title": "通路线索", "body": ["免疫炎症指标", "蛋白组筛选方向"]},
            {"stage": "03", "title": "动物验证", "body": ["整体模型复现", "验证关键通路异常"]},
            {"stage": "04", "title": "细胞闭环", "body": ["ROS/炎症/凋亡", "补足分子机制证据"]},
        ],
        "outputs": ["形成连续证据链", "支撑主结论", "服务论文答辩主线"],
    }


def build_study_board() -> dict[str, Any]:
    return {
        "kind": "study-board",
        "badge": "CLINICAL DESIGN",
        "summary": "把对象、分组、干预和评价压缩成一眼看懂的临床研究结构，并避免编号与正文互相遮挡。",
        "cards": [
            {"stage": "01", "title": "研究对象", "body": ["MDR-KP重症肺炎", "明确纳入与排除标准"]},
            {"stage": "02", "title": "分组设计", "body": ["设置对照与干预分组", "保证比较路径清晰"]},
            {"stage": "03", "title": "干预实施", "body": ["统一研究流程推进", "围绕关键节点随访"]},
            {"stage": "04", "title": "评价指标", "body": ["结局指标 + 机制指标", "服务最终主结论"]},
        ],
        "bottom_chips": ["对象清晰", "分组明确", "流程闭环", "评价聚焦"],
    }


def build_evidence_board() -> dict[str, Any]:
    return {
        "kind": "evidence-board",
        "badge": "EVIDENCE CHAIN",
        "summary": "证据链不是平铺堆叠，而是以主结论为核心，把四层证据组织成环抱式看板。",
        "cards": [
            {"title": "临床层", "body": ["症状改善", "预后指标向好"]},
            {"title": "分子层", "body": ["免疫炎症缓解", "差异蛋白筛选"]},
            {"title": "动物层", "body": ["关键通路异常可复现", "干预后出现逆转趋势"]},
            {"title": "细胞层", "body": ["ROS下降", "炎症与凋亡减轻"]},
        ],
        "center": {
            "title": "主结论",
            "body": "HQQD 通过自噬-炎症调控轴改善肺损伤，并支持临床获益",
        },
    }


def build_mechanism_clean(panels: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "kind": "mechanism-panels-clean",
        "summary": "机制页保留无字元素拼图，但把桥接句和说明移出图像主体，减少遮挡。",
        "panels": panels,
        "bridge_text": "HQQD 介入后，自噬与炎症调控趋于恢复",
    }


def update_slides(spec: dict[str, Any]) -> dict[str, Any]:
    refined = copy.deepcopy(spec)
    mechanism_panels: list[dict[str, str]] = []
    for slide in refined.get("slides", []):
        if slide.get("id") == "slide-32":
            mechanism_panels = slide.get("diagram_v4", {}).get("panels", [])
            break

    for slide in refined.get("slides", []):
        slide_id = slide.get("id")
        if slide_id == "slide-09":
            slide["diagram_v5"] = build_route_board()
            slide["takeaway"] = "技术路线页切换成高密度路线看板：中枢问题、四级主线和输出区全部在同一张原生 PPT 看板中。"
        elif slide_id == "slide-12":
            slide["diagram_v5"] = build_study_board()
            slide["takeaway"] = "方法页采用时间轴式研究设计看板，编号、卡片和正文彻底分层，减少重叠和拥挤。"
        elif slide_id == "slide-31":
            slide["diagram_v5"] = build_evidence_board()
            slide["takeaway"] = "证据链页改成主结论居中、四层证据环抱的看板式布局，不再只是横排卡片。"
        elif slide_id == "slide-32":
            slide["diagram_v5"] = build_mechanism_clean(mechanism_panels)
            slide["takeaway"] = "机制页保留三块无字元素，但让桥接说明和标签都避开图像主体，减少遮挡。"

    refined["schema_version"] = "0.9"
    refined["visual_pass"] = {
        "stage": "v5",
        "strategy": "dense-native-route-boards",
    }
    return refined


def main() -> None:
    parser = argparse.ArgumentParser(description="Build V5 dense visual spec from the V4 review spec.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--output-spec-file", required=True)
    parser.add_argument("--plan-file", required=True)
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    refined = update_slides(spec)
    write_json(Path(args.output_spec_file), refined)
    write_json(
        Path(args.plan_file),
        {
            "schema_version": "0.1",
            "stage": "v5",
            "diagram_shift": [
                "slide-09: dense route board with center hub and output band",
                "slide-12: timeline-style study board with external numbering rail",
                "slide-31: evidence board with centered thesis conclusion",
                "slide-32: cleaned hybrid mechanism layout with labels kept outside the art",
            ],
        },
    )


if __name__ == "__main__":
    main()
