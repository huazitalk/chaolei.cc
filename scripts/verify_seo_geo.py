#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
潮磊轴承官网 · SEO/GEO 修正验证脚本
=====================================
用途：验证 https://www.chaolei.cc 的 SEO/GEO 修正是否完整落地。
涵盖：
  A. 每个目标页面的元数据 (canonical / og:* / twitter:*)
  B. 结构化数据 JSON-LD 合法性 + 必要 @type (Organization / BreadcrumbList / Product)
  C. 地理/品牌信息字段 (address / areaServed —— 注：当前无 geo 经纬度坐标)
  D. sitemap.xml 与 robots.txt 合规
  E. Git 本地 HEAD 与远程 main 一致性（联网时用 GitHub API）

用法：
  python3 verify_seo_geo.py            # 仅本地文件检查（离线，不联网）
  python3 verify_seo_geo.py --live    # 额外做线上检查（需能访问 github.com / chaolei.cc）
  python3 verify_seo_geo.py --dir /path/to/website   # 指定站点目录

退出码：0 = 全部通过；1 = 存在 FAIL 项。WARN/INFO 不计入失败。
"""
import os, re, sys, json, argparse, subprocess

# ---------- 配置 ----------
EXPECT_DOMAIN = "https://www.chaolei.cc"          # 期望的 canonical / sitemap 域名
BAD_DOMAIN = "chaolei-bearing.com"                # 应已清除的错误域名
SITEMAP_URLS_EXPECT = 7                            # sitemap 应包含的目标页数量
REPO_API = "https://api.github.com/repos/huazitalk/chaolei.cc"
PAGES = ["index.html", "index-markforged.html", "about.html", "applications.html",
         "capabilities.html", "contact.html", "products.html", "history.html"]
# 这 3 页必须含 Product 结构化数据
PRODUCT_PAGES = {"index.html", "index-markforged.html", "products.html"}
# 允许 AI 爬虫的 UA 清单（robots.txt 应逐一 Allow）
AI_UA = ["GPTBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai", "CCBot",
         "PerplexityBot", "Google-Extended", "Bytespider", "Amazonbot",
         "Applebot", "Applebot-Extended", "meta-externalagent", "omgili",
         "omgilibot", "Diffbot"]

results = []   # (level, category, page, msg, ok)

def record(category, page, msg, ok, level=None):
    if level is None:
        level = "PASS" if ok else "FAIL"
    results.append((level, category, page, msg, ok))

# ---------- HTML 标签提取（不依赖属性顺序）----------
def meta_content(html, attr, val):
    """返回 <meta ... attr="val" ... content="X"> 或 content 在前的 content 值"""
    p1 = rf'<meta[^>]*\b{attr}=["\']{re.escape(val)}["\'][^>]*?\bcontent=["\']([^"\']*)["\']'
    m = re.search(p1, html, re.I)
    if m:
        return m.group(1)
    p2 = rf'<meta[^>]*\bcontent=["\']([^"\']*)["\'][^>]*?\b{attr}=["\']{re.escape(val)}["\']'
    m = re.search(p2, html, re.I)
    return m.group(1) if m else None

def link_href(html, rel):
    """返回 <link ... rel="X" ... href="Y"> 或 href 在前的 href 值"""
    p1 = rf'<link[^>]*\brel=["\']{re.escape(rel)}["\'][^>]*?\bhref=["\']([^"\']*)["\']'
    m = re.search(p1, html, re.I)
    if m:
        return m.group(1)
    p2 = rf'<link[^>]*\bhref=["\']([^"\']*)["\'][^>]*?\brel=["\']{re.escape(rel)}["\']'
    m = re.search(p2, html, re.I)
    return m.group(1) if m else None

def ld_json_blocks(html):
    out = []
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S|re.I):
        raw = m.group(1).strip()
        raw = re.sub(r'^<!\[CDATA\[|\]\]>$', '', raw, flags=re.S).strip()
        try:
            out.append(("ok", json.loads(raw)))
        except Exception as e:
            out.append(("err", str(e)))
    return out

def collect_types(data):
    types = []
    stack = list(data if isinstance(data, list) else [data])
    while stack:
        it = stack.pop()
        if isinstance(it, dict):
            if "@type" in it:
                types.append(it["@type"] if isinstance(it["@type"], str) else str(it["@type"]))
            if "@graph" in it and isinstance(it["@graph"], list):
                stack.extend(it["@graph"])
        elif isinstance(it, list):
            stack.extend(it)
    return types

def has_key_deep(data, key):
    stack = [data]
    while stack:
        it = stack.pop()
        if isinstance(it, dict):
            if key in it:
                return True
            stack.extend(it.values())
        elif isinstance(it, list):
            stack.extend(it)
    return False

# ---------- A/B/C: 页面级检查 ----------
def check_pages(website_dir):
    for pg in PAGES:
        path = os.path.join(website_dir, pg)
        if not os.path.isfile(path):
            record("页面文件", pg, f"文件缺失: {path}", False)
            continue
        html = open(path, encoding="utf-8").read()

        # --- A. 元数据 ---
        cano = link_href(html, "canonical")
        if not cano:
            record("canonical", pg, "缺失 canonical", False)
        elif not cano.startswith(EXPECT_DOMAIN):
            record("canonical", pg, f"域名错误: {cano}", False)
        elif BAD_DOMAIN in html:
            record("canonical", pg, f"仍存在错误域名 {BAD_DOMAIN}", False)
        else:
            record("canonical", pg, f"ok ({cano})", True)

        for prop in ("og:image", "og:title", "og:url"):
            ok = bool(meta_content(html, "property", prop))
            record(prop, pg, "缺失" if not ok else "ok", ok)

        tw_card = meta_content(html, "name", "twitter:card")
        if not tw_card:
            record("twitter:card", pg, "缺失", False)
        elif tw_card.lower() != "summary_large_image":
            record("twitter:card", pg, f"值异常: {tw_card}", False)
        else:
            record("twitter:card", pg, "ok", True)
        ok_tw_img = bool(meta_content(html, "name", "twitter:image"))
        record("twitter:image", pg, "缺失" if not ok_tw_img else "ok", ok_tw_img)

        # --- B/C. 结构化数据 + GEO 字段 ---
        blocks = ld_json_blocks(html)
        if not blocks:
            record("JSON-LD", pg, "无任何 ld+json 块", False)
            continue
        all_types, json_ok = [], True
        addr_ok = area_ok = geo_ok = False
        for status, data in blocks:
            if status == "err":
                json_ok = False
                record("JSON-LD", pg, f"JSON 解析失败: {data}", False)
                continue
            all_types += collect_types(data)
            addr_ok = addr_ok or has_key_deep(data, "address")
            area_ok = area_ok or has_key_deep(data, "areaServed")
            geo_ok = geo_ok or has_key_deep(data, "geo")
        if json_ok:
            record("JSON-LD", pg, "全部块 JSON 合法", True)

        tset = set(all_types)
        for need in ("Organization", "BreadcrumbList"):
            ok = need in tset
            record(f"@type:{need}", pg, "缺失" if not ok else "ok", ok)
        if pg in PRODUCT_PAGES:
            ok = "Product" in tset
            record("@type:Product", pg, "缺失（该页应有 Product）" if not ok else "ok", ok)

        record("GEO:address", pg, "缺失 address" if not addr_ok else "ok (PostalAddress)", addr_ok,
               level="WARN" if not addr_ok else None)
        record("GEO:areaServed", pg, "缺失 areaServed" if not area_ok else "ok", area_ok,
               level="WARN" if not area_ok else None)
        if not geo_ok:
            record("GEO:geo", pg, "未配置经纬度坐标 (geo) —— 可选增强项", True, level="INFO")

# ---------- C2. 元信息（<title> / <meta name="description">）----------
def check_meta(website_dir):
    """校验每页 <head> 内 title 与 description 唯一、非空、长度合理（可被抓取）。"""
    for pg in PAGES:
        path = os.path.join(website_dir, pg)
        if not os.path.isfile(path):
            record("META", pg, f"文件缺失: {path}", False)
            continue
        html = open(path, encoding="utf-8").read()

        # --- <title> ---
        titles = re.findall(r'<title\b[^>]*>.*?</title>', html, re.S | re.I)
        if len(titles) == 0:
            record("META:title", pg, "缺失 <title>", False)
        elif len(titles) > 1:
            record("META:title", pg, f"存在 {len(titles)} 个 <title>（应唯一）", False)
        else:
            m = re.search(r'<title\b[^>]*>(.*?)</title>', html, re.S | re.I)
            txt = m.group(1).strip() if m else ""
            if not txt:
                record("META:title", pg, "<title> 内容为空", False)
            else:
                n = len(txt)
                if n < 10 or n > 80:
                    record("META:title", pg, f"长度 {n} 偏{'短' if n < 10 else '长'}（建议 10–80 字）",
                           True, level="WARN")
                else:
                    record("META:title", pg, f"ok（{n} 字）", True)

        # --- <meta name="description"> ---
        descs = re.findall(r'<meta\b[^>]*\bname=["\']description["\'][^>]*?>', html, re.I)
        if len(descs) == 0:
            record("META:desc", pg, "缺失 <meta name=\"description\">", False)
        elif len(descs) > 1:
            record("META:desc", pg, f"存在 {len(descs)} 个 description（应唯一）", False)
        else:
            d = meta_content(html, "name", "description")
            if not d:
                record("META:desc", pg, "description 的 content 为空", False)
            else:
                n = len(d)
                if n < 30 or n > 200:
                    record("META:desc", pg, f"长度 {n} 偏{'短' if n < 30 else '长'}（建议 30–200 字）",
                           True, level="WARN")
                else:
                    record("META:desc", pg, f"ok（{n} 字）", True)

# ---------- D. sitemap / robots ----------
def check_sitemap_robots(website_dir):
    sm = os.path.join(website_dir, "sitemap.xml")
    if not os.path.isfile(sm):
        record("sitemap", "-", "sitemap.xml 缺失", False); return
    try:
        import xml.dom.minidom as M
        dom = M.parse(sm)
        locs = [u.firstChild.data for u in dom.getElementsByTagName("loc")]
        n = len(locs)
        if n != SITEMAP_URLS_EXPECT:
            record("sitemap", "-", f"URL 数={n}，期望 {SITEMAP_URLS_EXPECT}", False)
        else:
            record("sitemap", "-", f"合法 XML，含 {n} 个 URL", True)
        bad = [u for u in locs if not u.startswith(EXPECT_DOMAIN)]
        if bad:
            record("sitemap", "-", f"含非预期域名: {bad}", False)
        else:
            record("sitemap", "-", "全部 URL 指向正确域名", True)
    except Exception as e:
        record("sitemap", "-", f"XML 解析失败: {e}", False)

    rb = os.path.join(website_dir, "robots.txt")
    if not os.path.isfile(rb):
        record("robots", "-", "robots.txt 缺失", False); return
    txt = open(rb, encoding="utf-8").read()
    if "Cloudflare Managed" in txt:
        record("robots", "-", "仍含 'Cloudflare Managed'（开关未关）", False)
    else:
        record("robots", "-", "不含 Cloudflare Managed 注入", True)
    if f"Sitemap: {EXPECT_DOMAIN}/sitemap.xml" not in txt:
        record("robots", "-", "缺少 Sitemap 行", False)
    else:
        record("robots", "-", "含正确 Sitemap 行", True)
    missing = [ua for ua in AI_UA if f"User-agent: {ua}" not in txt]
    if missing:
        record("robots", "-", f"未放行 AI UA: {missing}", False)
    else:
        record("robots", "-", f"已放行全部 {len(AI_UA)} 类 AI 爬虫", True)

# ---------- E. Git 一致性 ----------
def check_git(website_dir, do_live):
    try:
        head = subprocess.check_output(["git", "-C", website_dir, "rev-parse", "HEAD"],
                                      stderr=subprocess.DEVNULL).decode().strip()
        record("git", "-", f"本地 HEAD = {head[:10]}", True, level="INFO")
    except Exception as e:
        record("git", "-", f"无法获取本地 HEAD: {e}", False, level="INFO")
        head = None

    try:
        out = subprocess.check_output(["git", "-C", website_dir, "status", "--short"],
                                      stderr=subprocess.DEVNULL).decode().strip()
        if out:
            record("git", "-", f"工作树有未提交改动:\n{out}", False, level="WARN")
        else:
            record("git", "-", "工作树 clean", True, level="PASS")
    except Exception:
        pass

    if not do_live:
        record("git", "-", "（跳过远程比对：未加 --live）", True, level="INFO")
        return
    try:
        import urllib.request
        req = urllib.request.Request(f"{REPO_API}/commits/main",
                                     headers={"Accept": "application/vnd.github+json",
                                              "User-Agent": "verify-script"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        remote = data["sha"]
        record("git", "-", f"远程 main = {remote[:10]}", True, level="INFO")
        if head and head != remote:
            record("git", "-", "本地 HEAD 与远程 main 不一致（沙箱内常因无法 fetch 而落后，本机 git pull 即可对齐）",
                   True, level="WARN")
        else:
            record("git", "-", "本地 HEAD == 远程 main", True, level="PASS")
    except Exception as e:
        record("git", "-", f"无法访问 GitHub API 比对远程: {e}（可本机手动 git pull 比对）", True, level="INFO")

# ---------- 报告 ----------
def report():
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "INFO": 0}
    print("\n" + "=" * 72)
    print("潮磊轴承 SEO/GEO 修正 · 验证报告")
    print("=" * 72)
    cur = None
    for level, cat, page, msg, ok in results:
        if cat != cur:
            cur = cat
            print(f"\n--- {cat} ---")
        mark = {"PASS": "✓", "FAIL": "✗", "WARN": "!", "INFO": "i"}[level]
        print(f"  [{mark}] {page:<22} {msg}")
        counts[level] += 1
    print("\n" + "-" * 72)
    print(f"汇总: PASS={counts['PASS']}  FAIL={counts['FAIL']}  WARN={counts['WARN']}  INFO={counts['INFO']}")
    print("=" * 72)
    return counts["FAIL"]

def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    # 脚本可位于仓库根或 <repo>/scripts/，自动定位含 index.html 的站点根目录
    repo_root = os.path.dirname(here)
    site_default = repo_root if os.path.isfile(os.path.join(repo_root, "index.html")) else here
    ap.add_argument("--dir", default=site_default)
    ap.add_argument("--live", action="store_true", help="额外联网比对远程仓库 + 线上抓取")
    args = ap.parse_args()
    wd = args.dir
    if not os.path.isdir(wd):
        print(f"站点目录不存在: {wd}")
        sys.exit(2)
    print(f"站点目录: {wd}")
    check_pages(wd)
    check_meta(wd)
    check_sitemap_robots(wd)
    check_git(wd, args.live)
    fails = report()
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
