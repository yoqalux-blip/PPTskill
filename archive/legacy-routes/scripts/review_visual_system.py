from __future__ import annotations

import argparse
from pathlib import Path

from common_io import read_json, write_text


def issue_count(spec: dict, plan: dict) -> dict:
    sparse_pages = 0
    figure_pages = 0
    long_labels = 0
    crowded_figures = 0

    figure_slide_ids = {asset["slide_id"] for asset in plan.get("assets", [])}
    for slide in spec.get("slides", []):
        if len(slide.get("bullets", [])) <= 2 and slide.get("layout") not in {"title", "section"}:
            sparse_pages += 1
        if slide.get("id") in figure_slide_ids:
            figure_pages += 1

    for asset in plan.get("assets", []):
        nodes = asset.get("payload", {}).get("nodes", [])
        if len(nodes) > asset.get("review_targets", {}).get("max_nodes", 8):
            crowded_figures += 1
        for node in nodes:
            label = node.get("label", "")
            if len(label) > asset.get("review_targets", {}).get("max_label_chars", 18):
                long_labels += 1

    return {
        "sparse_pages": sparse_pages,
        "figure_pages": figure_pages,
        "long_labels": long_labels,
        "crowded_figures": crowded_figures,
    }


def asset_score(asset: dict) -> tuple[int, list[str]]:
    score = 100
    notes: list[str] = []
    targets = asset.get("review_targets", {})
    nodes = asset.get("payload", {}).get("nodes", [])

    if len(nodes) > targets.get("max_nodes", 8):
        score -= 12
        notes.append("节点偏多，阅读负担较高。")

    overlong = 0
    for node in nodes:
        if len(node.get("label", "")) > targets.get("max_label_chars", 18):
            overlong += 1
    if overlong:
        score -= min(18, overlong * 4)
        notes.append("存在偏长标签，建议继续压缩节点文本。")

    if asset.get("layout_hint") == "figure-full":
        notes.append("适合远距离展示，建议保留 2-3 条解释性 bullet。")
    else:
        notes.append("适合图文并置展示，需保证文本区不要再次堆满。")

    if not notes:
        notes.append("图形结构清晰，可直接进入版面微调阶段。")
    return max(score, 0), notes


def report_markdown(spec: dict, plan: dict) -> str:
    counts = issue_count(spec, plan)
    lines = [
        "# Visual Review V2",
        "",
        "## 系统概览",
        f"- 全部页面：{len(spec.get('slides', []))} 页",
        f"- 已接入图形页面：{counts['figure_pages']} 页",
        f"- 仍偏稀疏的纯文字页面：{counts['sparse_pages']} 页",
        f"- 过长图形标签：{counts['long_labels']} 处",
        f"- 可能偏拥挤的图形：{counts['crowded_figures']} 张",
        "",
        "## 图形逐项审查",
    ]

    for asset in plan.get("assets", []):
        score, notes = asset_score(asset)
        lines.append(f"### {asset['slide_title']}")
        lines.append(f"- 图形类型：`{asset['visual_type']}`")
        lines.append(f"- 布局建议：`{asset['layout_hint']}`")
        lines.append(f"- 视觉评分：`{score}/100`")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.extend(
        [
            "## 审美结论",
            "- 当前图形系统已经从“纯文字答辩稿”升级为“图文协同答辩稿”。",
            "- 机制图与技术路线图已经具备继续精修的基础，后续重点应转向图表替换和图面细节。",
            "- 下一轮优先事项应是：替换关键结果页的示意图或统计图、继续细化模块三的动物实验视觉表达、统一图标题与图注的措辞风格。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Review visual assets and page-level visual coverage.")
    parser.add_argument("--spec-file", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    spec = read_json(Path(args.spec_file))
    plan = read_json(Path(args.plan_file))
    write_text(Path(args.output_file), report_markdown(spec, plan))


if __name__ == "__main__":
    main()
