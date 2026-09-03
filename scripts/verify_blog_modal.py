#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
博客列表页改造后的上线前校验（零三方依赖，仅标准库）。

校验项
------
1. 三张卡片均走弹窗分支（无 data-href 残留），且各自对应一个 <template>
2. HTML 标签配平（剔除 script / style / 注释后统计，避免注释里的标签文本误计）
3. JSON-LD 可被 json.loads 解析
4. 模板内锚点 href="#x" 与 id="x" 一一对应（无死链）
5. 模板内 id 不与页面既有 id 冲突
6. 属性值破损检查（data-i18n 被嵌套属性打断这类事故）
7. 尺寸表/目录所需样式类在页面 style 段有定义，且含移动端断点
8. i18n 英文词条覆盖（对比既有两篇模板的基线水平）

用法
----
    python3 scripts/verify_blog_modal.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog" / "index.html"
I18N = ROOT / "js" / "i18n-data.js"

passed, warned, failed = [], [], []


def check(cond: bool, pass_msg: str, fail_msg: str, level: str = "err") -> None:
    """cond 为真记 passed（打印 pass_msg），否则按 level 记 warn / failed（打印 fail_msg）。"""
    if cond:
        passed.append(pass_msg)
    elif level == "warn":
        warned.append(fail_msg)
    else:
        failed.append(fail_msg)


raw = BLOG.read_text(encoding="utf-8")

# 剔除 script / style / HTML 注释，避免注释或 JS 字符串里的标签文本被计入配平
stripped = re.sub(r"<script\b.*?</script>", "", raw, flags=re.S)
stripped = re.sub(r"<style\b.*?</style>", "", stripped, flags=re.S)
stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.S)

# ---------- 1. 卡片 ↔ 模板配对 ----------
cards = re.findall(r'<article class="article-card"[^>]*data-article="([^"]+)"([^>]*)>', raw)
check(len(cards) == 3, f"文章卡片数量 = {len(cards)}", f"文章卡片数量异常：{len(cards)}（应为 3）")
for name, rest in cards:
    check(
        "data-href" not in rest,
        f'卡片 "{name}" 走弹窗分支（无 data-href）',
        f'卡片 "{name}" 仍带 data-href，会走直跳而非弹窗',
    )
    check(
        f'<template id="tpl-{name}">' in raw,
        f'卡片 "{name}" 已配对 <template id="tpl-{name}">',
        f'卡片 "{name}" 缺少对应模板',
    )

# ---------- 2. 标签配平 ----------
for tag in ["div", "ul", "ol", "li", "table", "article", "section", "nav", "dl", "template"]:
    o = len(re.findall(rf"<{tag}[\s>]", stripped))
    c = len(re.findall(rf"</{tag}>", stripped))
    check(o == c, f"<{tag}> 配平（{o} 组）", f"<{tag}> 不配平：开 {o} / 闭 {c}")

# ---------- 3. JSON-LD ----------
ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S)
check(bool(ld_blocks), f"存在 {len(ld_blocks)} 段 JSON-LD", "未找到 JSON-LD")
for i, m in enumerate(ld_blocks, 1):
    try:
        data = json.loads(m)
        passed.append(f"JSON-LD #{i} 解析通过（@graph {len(data.get('@graph', []))} 项）")
    except json.JSONDecodeError as e:
        failed.append(f"JSON-LD #{i} 解析失败：{e}")

# ---------- 4 & 5. 锚点与 id 冲突 ----------
tpl_blocks = re.findall(r'<template id="tpl-([^"]+)">(.*?)</template>', raw, re.S)
page_ids = set(re.findall(r'\sid="([^"]+)"', re.sub(r"<template\b.*?</template>", "", raw, flags=re.S)))
for name, body in tpl_blocks:
    hrefs = set(re.findall(r'href="#([^"]+)"', body))
    ids = set(re.findall(r'\sid="([^"]+)"', body))
    check(
        not (hrefs - ids),
        f'模板 tpl-{name} 锚点全部有效（{len(hrefs)} 个）' if hrefs else f"模板 tpl-{name} 无内部锚点",
        f'模板 tpl-{name} 锚点死链：{sorted(hrefs - ids)}',
    )
    check(
        not (ids & page_ids),
        f"模板 tpl-{name} 的 id 与页面无冲突",
        f'模板 tpl-{name} 的 id 与页面既有 id 冲突：{sorted(ids & page_ids)}',
    )

# ---------- 6. 属性破损 ----------
nested = re.findall(r'(?:data-i18n|data-i18n-attr|aria-label|alt|title)="[^"]{0,400}?\s[a-zA-Z-]+="', raw)
check(
    not nested,
    "属性值无嵌套打断",
    f"属性值被嵌套属性打断 {len(nested)} 处 → {[n[:60] for n in nested[:3]]}",
)

# ---------- 7. 样式定义 + 移动端断点 ----------
style_match = re.search(r"<style\b.*?</style>", raw, re.S)
style = style_match.group(0) if style_match else ""
for cls in ["size-wrap", "size-table", "toc-box", "def-list", "callout", "series-nav"]:
    used = any(cls in body for _, body in tpl_blocks)
    if used:
        check(
            re.search(rf"\.{cls}\s*[,{{ ]", style) is not None,
            f".{cls} 样式已定义",
            f"模板用到 .{cls} 但页面 style 段未定义",
        )
check(
    "max-width: 640px" in style,
    "含 640px 移动端断点",
    "缺少 640px 移动端响应式断点",
)

# CSS 花括号配平
check(style.count("{") == style.count("}"), f"style 段花括号配平（{style.count('{')} 对）",
      f"style 段花括号不配平：{style.count('{')} / {style.count('}')}")

# ---------- 8. i18n 覆盖 ----------
if I18N.exists():
    i18n_src = I18N.read_text(encoding="utf-8")

    def coverage(bodies: list[str]) -> tuple[int, int]:
        keys = set()
        for b in bodies:
            # html.unescape 对齐浏览器 getAttribute 口径（如 &gt; → >）
            keys |= {k for k in (html.unescape(r) for r in re.findall(r'data-i18n="([^"]+)"', b)) if k}
        hit = sum(1 for k in keys if f'"{k}"' in i18n_src or f"'{k}'" in i18n_src)
        return hit, len(keys)

    baseline = coverage([b for n, b in tpl_blocks if n in ("608", "folding")])
    new_hit, new_total = coverage([b for n, b in tpl_blocks if n == "size-chart"])
    if new_total:
        rate = new_hit / new_total * 100
        base_rate = baseline[0] / baseline[1] * 100 if baseline[1] else 0
        msg = (
            f"尺寸手册模板英文词条覆盖 {new_hit}/{new_total}（{rate:.0f}%）；"
            f"既有两篇基线 {baseline[0]}/{baseline[1]}（{base_rate:.0f}%）"
        )
        check(rate >= 80, msg, msg + " → 低于 80%，EN 版会有较多中文残留（i18n.js 降级保留中文，不会空白）", level="warn")

# ---------- 输出 ----------
def dump(title: str, items: list[str]) -> None:
    if not items:
        return
    print("=" * 70)
    print(title)
    print("=" * 70)
    for m in items:
        print(("  " + m) if m.startswith("     ") else "  • " + m)
    print()


dump("通过", passed)
dump("提醒（不阻塞）", warned)
dump("失败", failed)

print(f"体积：{len(raw.encode('utf-8')):,} 字节")
print("结论：" + ("全部通过" if not failed else f"{len(failed)} 项需修复"))
raise SystemExit(1 if failed else 0)
