# Visual QA Loop

## Goal

Turn slide review into a repeatable pipeline instead of a one-shot manual glance.

## Loop

1. Render the current deck spec into a local `.pptx`.
2. Export each slide to `.png` through local PowerPoint automation.
3. Audit the rendered deck for:
   - text overlap
   - text intruding into image regions
   - text boxes too dense for their available area
   - page-level text density that makes a slide feel crowded
4. Apply conservative repairs to the deck spec.
5. Rerender and audit again.
6. Stop when high-severity issues disappear or the loop reaches its iteration cap.

## Why This Matters

- 技术路线图和研究设计页常常不是“内容错”，而是“空间关系错”。
- 机制页和复杂看板页在 spec 层看起来合理，真正渲染后才会暴露遮挡与拥挤。
- 用固定的 QA 回路可以把“我感觉不太对”转成可记录、可迭代、可收敛的过程。

## Current Scope

- 已支持本地 PowerPoint 导图。
- 已支持对 `.pptx` 几何结构做重叠、拥挤和压缩风险审计。
- 已支持对部分高密度 `V5` 布局做保守返修。

## Next Scope

- 对 route board / study board / evidence board 增加更细的局部热点诊断。
- 把“失败页”自动映射回具体布局母版，而不只是压缩文字。
- 为后续模型视觉评审器预留接口，让图像审美评分和几何审计结合。
