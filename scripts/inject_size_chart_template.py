#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把「微型深沟球轴承型号尺寸对照手册」正文抽取为 blog/index.html 的浮窗模板。

用途
----
尺寸手册此前是列表页唯一「直跳独立页」的卡片。本次改造要让它与另两篇
（folding / 608）保持一致，复用现有 #blogModal 弹窗打开，因此需要在
blog/index.html 内补一个 <template id="tpl-size-chart">，供现有 openBlog()
按 data-article="size-chart" 自动挂载。

做法
----
1. 从 blog/miniature-bearing-size-chart.html 抽取 .article-body 容器内部内容；
2. 剥掉页面编辑器产物 data-page-node-id（另两个模板同样不带该属性，且能省一半体积）；
3. 包成 <template id="tpl-size-chart"><div class="article-body">…</div></template>，
   结构与 tpl-608 / tpl-folding 完全一致；
4. 插入到 blog/index.html 中 tpl-folding 收尾 </template> 之后。

约束
----
- 幂等：重复执行不会产生第二个 tpl-size-chart；
- 不改动现有 JS 逻辑，不引入新的弹窗方案；
- 只改 blog/index.html，不动其他页面。

用法
----
    python3 scripts/inject_size_chart_template.py            # 执行
    python3 scripts/inject_size_chart_template.py --dry-run  # 只看统计，不落盘
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "blog" / "miniature-bearing-size-chart.html"
IDX = ROOT / "blog" / "index.html"

TEMPLATE_ID = "tpl-size-chart"
ANCHOR_TEMPLATE_ID = "tpl-folding"


def extract_body(src_text: str) -> str:
    """抽取 .article-body 容器内部内容，并剥掉 data-page-node-id。"""
    lines = src_text.split("\n")

    start = next(
        (i for i, l in enumerate(lines) if 'class="container container-sm article-body"' in l),
        None,
    )
    if start is None:
        sys.exit("✗ 未找到 .article-body 起始容器")

    # 从后往前找：紧挨着 </article> 的那个 </div> 即正文容器收尾
    end = next(
        (
            i
            for i in range(len(lines) - 1, 0, -1)
            if lines[i].strip() == "</div>" and lines[i + 1].strip() == "</article>"
        ),
        None,
    )
    if end is None:
        sys.exit("✗ 未找到 .article-body 收尾 </div>")

    inner = "\n".join(lines[start + 1:end]).strip("\n")

    # 剥掉页面编辑器节点标记（另两个模板均无此属性，保持结构一致 + 省体积）
    inner = re.sub(r'\sdata-page-node-id="[^"]*"', "", inner)
    return inner


def build_template(inner: str) -> str:
    """包成与 tpl-608 / tpl-folding 同构的 template 片段。"""
    return (
        f'\n<!-- 文章完整内容模板：微型深沟球轴承型号尺寸对照手册（68/69/60/62/63/MR/R/F 全系列） -->\n'
        f'<template id="{TEMPLATE_ID}">\n'
        f'<div class="article-body">\n'
        f"{inner}\n"
        f"</div>\n"
        f"</template>\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="注入尺寸手册浮窗模板到 blog/index.html")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写文件")
    args = ap.parse_args()

    src_text = SRC.read_text(encoding="utf-8")
    idx_text = IDX.read_text(encoding="utf-8")

    inner = extract_body(src_text)
    block = build_template(inner)

    # —— 幂等：已存在则整体替换，不产生第二个模板 ——
    existing = re.search(
        rf'\n?<!-- 文章完整内容模板：微型深沟球轴承型号尺寸对照手册[^\n]*-->\n'
        rf'<template id="{TEMPLATE_ID}">.*?</template>\n',
        idx_text,
        re.S,
    )

    if existing:
        mode = "替换已有模板"
        new_idx = idx_text[: existing.start()] + block + idx_text[existing.end():]
    else:
        anchor = re.search(
            rf'<template id="{ANCHOR_TEMPLATE_ID}">.*?</template>\n',
            idx_text,
            re.S,
        )
        if not anchor:
            sys.exit(f"✗ 未找到锚点 <template id=\"{ANCHOR_TEMPLATE_ID}\">")
        mode = "新增模板"
        new_idx = idx_text[: anchor.end()] + block + idx_text[anchor.end():]

    before, after = len(idx_text.encode("utf-8")), len(new_idx.encode("utf-8"))
    print(f"来源      ：{SRC.relative_to(ROOT)}")
    print(f"正文      ：{len(inner.encode('utf-8')):,} 字节（已剥离 data-page-node-id）")
    print(f"模板块    ：{len(block.encode('utf-8')):,} 字节")
    print(f"操作      ：{mode}")
    print(f"blog/index.html：{before:,} → {after:,} 字节（+{after - before:,}）")

    if args.dry_run:
        print("\n--dry-run：未写入文件")
        return 0

    IDX.write_text(new_idx, encoding="utf-8")
    print("\n✓ 已写入 blog/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
