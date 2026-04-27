# draw.io MCP Integration

## Positioning

draw.io MCP is worth borrowing, but it should not replace every existing visual backend.

Use it as an optional `diagram-lab` backend for pages that are:

- more complex than simple PPT cards and arrows
- still primarily logical rather than painterly
- likely to benefit from a manually editable source file

## Best-fit Use Cases

- 技术路线总览图
- 研究设计图
- 证据链整合图
- 系统架构图
- 时序图或角色交互图

## Not a Good Primary Backend For

- 统计图
- 机制示意图中的生物学美术元素
- 需要完全继承 PPT 字体和边框系统的轻量页面

## Why It Helps

- draw.io provides a richer stencil and diagram vocabulary than our current native PPT cards alone.
- An editable `.drawio` source is valuable when a route board needs manual polishing after AI drafting.
- The MCP path can create diagrams from Mermaid, CSV, or XML-oriented inputs before exporting to SVG or PNG.

## Why It Should Stay Optional

- 自动生成的 draw.io 图并不会天然解决排版问题。
- Mermaid/XML 生成的复杂图依然可能出现文字遮挡、布局混乱和图文错位。
- 对于中文答辩 PPT，最终页面字体系统和留白控制仍然更适合由本地 PPT 渲染器统一收口。

## Recommended Architecture

1. `deck-spec` determines whether a page is simple enough for native PPT geometry.
2. If a page is a high-complexity route board, route it to draw.io MCP.
3. Generate a draft from Mermaid / CSV / XML through draw.io MCP.
4. Keep the `.drawio` source as an intermediate artifact.
5. Export SVG or PNG for PPT insertion.
6. Prefer dropping the final asset into the same slide artifact directory with a stable name such as `exported.svg` or `exported.png` so the renderer can auto-discover it.
7. Run the visual QA loop.
8. If QA fails, repair either:
   - the draw.io source
   - the exported asset placement
   - or the consuming PPT layout

## Practical Recommendation For This Project

- Keep `native-ppt-diagram` as the default for most route/design/evidence pages.
- Introduce draw.io MCP only for pages that need denser route-board structures similar to high-information academic technical-route figures.
- Continue to use Nano Banana for no-text biological art and atmosphere assets.
- Continue to use the visual QA loop after draw.io export, because draw.io automation does not remove the need for post-render validation.

## Suggested Next Build

- Add a `drawio_backend` route in the visual planner.
- Save `.drawio` or XML intermediates under `runs/<name>/drawio/`.
- Add a `failed_visual_qa -> redraw_with_drawio` escalation rule for route-board pages.

## Implemented Local Entry Points

- `scripts/drawio_mcp_client.mjs`
  Use this as the local MCP bridge. It can list tools, open Mermaid drafts, or open XML drafts in the draw.io editor.
- `scripts/build_drawio_backend.py`
  Use this to generate editable draw.io lab artifacts from `deck-spec.json`. It writes per-slide `draft.xml`, `draft.mmd`, and `context.json` files plus a top-level `drawio-manifest.json`. On reruns it also scans each slide artifact directory for `SVG/PNG` exports and injects them into `drawio_backend.exported_asset`.
- `scripts/run_visual_qa_loop.py --drawio-on-fail`
  Use this to escalate failed route, design, and evidence slides into draw.io work orders during visual QA rounds.
- `scripts/normalize_pptx.ps1`
  Use this after rendering so the delivered PPTX is PowerPoint-normalized and no longer relies on the user manually clicking "Repair".

## Practical Workflow In This Project

1. Generate or refine a `deck-spec`.
2. Render and audit the PPT pages.
3. For failed complex logic pages, run `build_drawio_backend.py` or let the QA loop do it automatically.
4. Open the generated XML draft with:

```powershell
node .\scripts\drawio_mcp_client.mjs open-xml --content-file .\runs\<run>\drawio\<slide>\draft.xml
```

5. Polish the diagram in draw.io.
6. Export a stable `exported.svg` or `exported.png` for later PPT insertion, or use the edited XML as a human-reviewed diagram source.
7. Rebuild or rerender the deck so the draw.io asset is consumed automatically.
