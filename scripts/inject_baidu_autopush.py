#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
潮磊轴承官网 · 百度「自动推送」JS 注入工具
=========================================
向网站每个页面的 <head> 内嵌入百度主动推送（自动推送）JS，
使任意页面被访问时自动通知百度抓取。该脚本非阻塞、不阻塞解析、不影响渲染。

用法：
  python3 inject_baidu_autopush.py                # 注入 website/ 下全部 .html（递归）
  python3 inject_baidu_autopush.py --dir website  # 指定站点目录
  python3 inject_baidu_autopush.py a.html b.html  # 指定若干文件
  python3 inject_baidu_autopush.py --dry-run       # 仅报告将改动哪些文件，不写盘

特性：
  - 幂等：已含特征串则跳过，不会重复注入
  - 位置正确：仅插入到 </head> 之前
  - 零依赖：仅用标准库（re），便于在任何环境直接运行
  - 递归扫描子目录，覆盖（重新运行即可补全）动态生成 / 新加的页面

说明：百度官方「自动推送」JS 动态创建 <script> 并异步加载 push.js，
与本项目的 i18n 注入（inject_i18n.py）可并存——后者重序列化时不会删除已存在的 script。
"""
import os, sys, re, argparse

# 百度官方自动推送片段（会在运行时按协议 https/http 自动选择 push.js 地址）
SNIPPET = (
    '  <!-- 百度自动推送：页面被访问时自动通知百度抓取，非阻塞、不影响渲染 -->\n'
    '  <script>\n'
    '  (function(){\n'
    '      var bp = document.createElement(\'script\');\n'
    '      var curProtocol = window.location.protocol.split(\':\')[0];\n'
    '      if (curProtocol === \'https\') {\n'
    '          bp.src = \'https://zz.bdstatic.com/linksubmit/push.js\';\n'
    '      } else {\n'
    '          bp.src = \'http://push.zhanzhang.baidu.com/push.js\';\n'
    '      }\n'
    '      var s = document.getElementsByTagName(\'script\')[0];\n'
    '      s.parentNode.insertBefore(bp, s);\n'
    '  })();\n'
    '  </script>\n'
)

# 命中任一特征即视为已注入，避免重复
ALREADY_MARKERS = (
    'push.zhanzhang.baidu.com/push.js',
    'zz.bdstatic.com/linksubmit/push.js',
    '百度自动推送',
)

HEAD_CLOSE_RE = re.compile(r'</head\s*>', re.I)


def already_injected(html: str) -> bool:
    return any(m in html for m in ALREADY_MARKERS)


def inject(html: str):
    """在 </head> 之前插入片段；无 </head> 返回 None。"""
    m = HEAD_CLOSE_RE.search(html)
    if not m:
        return None
    pos = m.start()
    return html[:pos] + SNIPPET + html[pos:]


def main():
    ap = argparse.ArgumentParser(description="百度自动推送 JS 注入")
    ap.add_argument("files", nargs="*", help="指定文件（不填则扫描 --dir）")
    ap.add_argument("--dir", default="website", help="站点目录，默认 %(default)s（递归扫描 .html）")
    ap.add_argument("--dry-run", action="store_true", help="只报告将改动，不写盘")
    args = ap.parse_args()

    files = list(args.files)
    if not files:
        if not os.path.isdir(args.dir):
            print(f"站点目录不存在：{args.dir}", file=sys.stderr)
            sys.exit(2)
        for root, _, fs in os.walk(args.dir):
            for f in fs:
                if f.endswith(".html"):
                    files.append(os.path.join(root, f))
    files = sorted(set(files))
    if not files:
        print("未发现 .html 文件")
        sys.exit(2)

    changed = skipped = failed = 0
    for f in files:
        try:
            html = open(f, encoding="utf-8").read()
        except Exception as e:
            print(f"[skip] {f}: 读取失败 {e}", file=sys.stderr)
            failed += 1
            continue
        if already_injected(html):
            print(f"[skip] {f}: 已含百度自动推送")
            skipped += 1
            continue
        new = inject(html)
        if new is None:
            print(f"[skip] {f}: 未找到 </head>", file=sys.stderr)
            failed += 1
            continue
        if args.dry_run:
            print(f"[would inject] {f}")
            changed += 1
            continue
        try:
            open(f, "w", encoding="utf-8").write(new)
        except Exception as e:
            print(f"[skip] {f}: 写入失败 {e}", file=sys.stderr)
            failed += 1
            continue
        print(f"[injected] {f}")
        changed += 1

    print(f"\n汇总：注入 {changed} | 已存在跳过 {skipped} | 失败 {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
