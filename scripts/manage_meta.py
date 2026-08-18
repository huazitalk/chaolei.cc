#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
潮磊轴承官网 · 页面元信息（<title> / <meta name="description">）集中管理脚本
============================================================================
目标：把各页面 <head> 中的 <title> 与 <meta name="description"> 变成「单一事实来源、
可配置、可重复注入」的资产，而非散落在 8 个 HTML 里手动维护。

机制：
  1. 配置集中在 meta-config.json：
       - default.title / default.description  → 站点级兜底（首页直接继承）
       - pages.<file>.title / pages.<file>.description → 逐页覆盖；值为 null 时继承 default
  2. 本脚本读取配置，对 website/ 下各页 head 做「注入 / 更新」：
       - 保证 <head> 内「唯一」的 <title> 与「唯一」的 <meta name="description">
       - 同步 i18n 属性（data-i18n / data-i18n-attr），保持中英双语切换可用
  3. 标签写入静态 HTML（非运行时 JS 注入），确保搜索引擎 / AI 爬虫直接抓到。

用法：
  python3 manage_meta.py                 # 按配置注入/更新全部页面
  python3 manage_meta.py --check         # 仅校验差异，不写文件（dry-run）
  python3 manage_meta.py --dir PATH      # 指定站点目录（默认：自动定位含 index.html 的仓库根）
  python3 manage_meta.py --config PATH   # 指定配置文件（默认：仓库根 meta-config.json）

后续更新：编辑 meta-config.json → 重新运行本脚本即可；全站统一用建议值只需把各页
          title/description 改为 null（自动套用 default）。
"""
import sys, os, json, argparse
from bs4 import BeautifulSoup, Tag

# ------------------------- 配置解析 -------------------------
def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def resolve(page_cfg, default):
    """逐页解析：null / 缺失 → 继承 default；否则用页面值。"""
    if not isinstance(page_cfg, dict):
        page_cfg = {}
    title = page_cfg.get("title")
    desc = page_cfg.get("description")
    return (
        title if title else default["title"],
        desc if desc else default["description"],
    )

# ------------------------- 标签操作 -------------------------
def set_title(soup, text):
    head = soup.head
    if head is None:
        raise RuntimeError("HTML 缺少 <head>，无法注入 title")
    existing = head.find("title")
    if existing:
        existing.clear()
        existing.string = text
    else:
        t = soup.new_tag("title")
        t.string = text
        vp = head.find("meta", attrs={"name": "viewport"})
        (vp.insert_after(t) if vp else head.insert(0, t))
        existing = t
    # i18n：让标题可被中英切换翻译
    existing["data-i18n"] = text
    # 保证唯一
    for extra in head.find_all("title")[1:]:
        extra.decompose()

def set_description(soup, text):
    head = soup.head
    existing = head.find("meta", attrs={"name": "description"})
    if existing is None:
        m = soup.new_tag("meta")
        m["name"] = "description"
        t = head.find("title")
        (t.insert_after(m) if t else head.insert(0, m))
        existing = m
    existing["content"] = text
    # i18n：同步翻译源
    existing["data-i18n-attr"] = json.dumps({"content": text}, ensure_ascii=False)
    # 保证唯一
    for extra in head.find_all("meta", attrs={"name": "description"})[1:]:
        extra.decompose()

# ------------------------- 主流程 -------------------------
def process_file(path, title, desc, dry_run):
    html = open(path, encoding="utf-8").read()
    soup = BeautifulSoup(html, "html.parser")
    set_title(soup, title)
    set_description(soup, desc)
    if dry_run:
        return None
    out = soup.encode("utf-8").decode("utf-8")
    open(path, "w", encoding="utf-8").write(out)

def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    # 脚本可位于仓库根或 <repo>/scripts/，自动定位含 index.html 的站点根目录
    repo_root = os.path.dirname(here)
    site_default = repo_root if os.path.isfile(os.path.join(repo_root, "index.html")) else here
    cfg_default = os.path.join(repo_root, "meta-config.json")
    if not os.path.isfile(cfg_default):
        cfg_default = os.path.join(here, "meta-config.json")
    ap.add_argument("--dir", default=site_default)
    ap.add_argument("--config", default=cfg_default)
    ap.add_argument("--check", action="store_true", help="仅校验，不写文件")
    args = ap.parse_args()

    cfg = load_config(args.config)
    default = cfg["default"]
    pages = cfg.get("pages", {})

    print(f"配置: {args.config}")
    print(f"站点: {default['title']}")
    print(f"{'模式':<6} {'页面':<22} {'title长度':>8} {'desc长度':>8}")
    print("-" * 56)

    changed = 0
    for fname, pcfg in pages.items():
        fpath = os.path.join(args.dir, fname)
        if not os.path.isfile(fpath):
            print(f"{'缺失':<6} {fname:<22} 文件不存在，跳过")
            continue
        title, desc = resolve(pcfg, default)
        cur = open(fpath, encoding="utf-8").read()
        soup_cur = BeautifulSoup(cur, "html.parser")
        cur_title = soup_cur.head.find("title").get_text(strip=True) if soup_cur.head and soup_cur.head.find("title") else ""
        cur_desc_tag = soup_cur.head.find("meta", attrs={"name": "description"}) if soup_cur.head else None
        cur_desc = cur_desc_tag.get("content", "") if cur_desc_tag else ""
        same = (cur_title == title and cur_desc == desc)

        print(f"{'校验' if args.check else ('OK' if same else '更新'):<6} "
              f"{fname:<22} {len(title):>8} {len(desc):>8}")
        if not same:
            changed += 1
            if not args.check:
                process_file(fpath, title, desc, dry_run=False)
    print("-" * 56)
    if args.check:
        print(f"差异页数量: {changed}（--check 未写文件）")
    else:
        print(f"已写入/确认页数量: {len(pages)}，其中变更: {changed}")
    print("完成。")

if __name__ == "__main__":
    main()
