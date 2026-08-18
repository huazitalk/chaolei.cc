#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
潮磊轴承官网 · 百度站长平台 URL 主动推送模块
============================================
向百度搜索资源平台「普通收录 - 主动推送(urls)」接口批量提交待收录 URL。

接口文档参考：
  https://ziyuan.baidu.com/college/courseinfo?id=267&page=2#h2_article_title5
（官方另提供 update / del 接口用于更新与删除已提交 URL，本模块一并支持。）

调用方式：POST，Content-Type: text/plain;charset=utf-8，请求体为「每行一个 URL」的纯文本。
成功响应（HTTP 200）示例：
  {"remain": 4999998, "success": 2, "not_same_site": 0, "not_valid": 0}
失败响应示例：
  {"error": 401, "message": "invalid token"}

依赖：仅 Python 标准库（urllib / json / socket），无需安装第三方包，便于直接集成到现有项目。

────────────────────────────────────────────
【命令行用法】
  # 直接传 URL
  python3 baidu_push.py --urls https://www.chaolei.cc/ https://www.chaolei.cc/products.html
  # 从文件读取（每行一个，# 开头的行为注释）
  python3 baidu_push.py --file urls.txt
  # 从标准输入读取（管道）
  cat urls.txt | python3 baidu_push.py
  # 更新 / 删除（而非新增推送）
  python3 baidu_push.py --action update --file urls.txt
  python3 baidu_push.py --action del    --file urls.txt
  # 从 sitemap.xml 读取 URL 并提交（默认异常不中断，继续推送剩余分片）
  python3 baidu_push.py --sitemap website/sitemap.xml
  # 任意来源批量推送 + 异常不中断
  python3 baidu_push.py --file urls.txt --safe

【作为模块导入】
  from baidu_push import BaiduPushClient
  client = BaiduPushClient()                       # 自动使用默认 site / token
  res = client.push([
      "https://www.chaolei.cc/products.html",
      "https://www.chaolei.cc/applications.html",
  ])
  print(res.success, res.remain)                   # 成功条数 / 当日剩余配额

  # 异常不中断的批量推送（推荐用于 CI / 定时任务）
  res = client.push_safe(urls)                     # res.errors 记录每个失败分片
  # 直接读取 sitemap.xml 中的 URL 并提交
  res = client.push_sitemap("website/sitemap.xml")  # 默认 safe=True，逐分片失败不中止

────────────────────────────────────────────

安全提示：百度接口 token 等同站点写入凭证。本仓库版本不硬编码 token，
必须通过环境变量 BAIDU_PUSH_TOKEN 提供（GitHub Actions 在 Settings → Secrets 配置后由工作流注入）。
"""
import os, sys, json, socket, argparse, re, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urlencode
from typing import Iterable, List, Optional


def _normalize_site(site: str) -> str:
    """百度接口要求 site 不带协议前缀（如 www.example.com，而非 https://www.example.com）。

    这里统一剥离 http://、https:// 前缀，避免把带协议的站点直接拼进请求而触发 400。
    """
    return re.sub(r"^https?://", "", (site or "").strip(), flags=re.I)


# ---------- 默认配置（取自你的站点接口）----------
DEFAULT_SITE  = "https://www.chaolei.cc"
API_HOST      = "http://data.zz.baidu.com"
MAX_URLS_PER_POST = 2000                 # 百度单次提交上限（官方限制 2000 条/次）

# token 优先从环境变量读取；未设置则回退到内嵌默认值（你的站点接口 token）
DEFAULT_TOKEN = os.environ.get("BAIDU_PUSH_TOKEN", "")  # 仓库内不硬编码 token；请通过环境变量 BAIDU_PUSH_TOKEN 注入

# 百度接口业务错误码 → 中文释义（响应体未携带 message 时回退使用）
ERROR_MESSAGES = {
    400: "请求参数错误（site/token 不匹配，或提交了不支持的 URL；也可能是当日配额已用尽——剩余配额不足时百度同样返回 400）",
    401: "校验失败（token 错误，或 site 与 token 不匹配）",
    404: "接口地址错误（请检查 endpoint 拼写）",
    500: "百度接口内部错误，请稍后重试",
}


class BaiduPushError(Exception):
    """百度推送相关错误：网络异常 / HTTP 错误 / 接口业务错误均归于此。"""
    def __init__(self, message: str, code: Optional[int] = None, raw: Optional[str] = None):
        self.code = code          # HTTP 状态码或百度业务错误码；网络异常时为 None
        self.message = message    # 已本地化的可读错误信息
        self.raw = raw            # 原始响应体，便于排查
        super().__init__(message)


@dataclass
class PushResult:
    """一次提交（可能含分批）的汇总结果。"""
    success: int = 0            # 成功推送的 URL 数
    remain: int = 0             # 当日剩余可提交配额
    not_same_site: int = 0      # 因「非本站 URL」被忽略的条数
    not_valid: int = 0          # 因「URL 格式不合法」被忽略的条数
    total: int = 0             # 实际提交（去重后）的 URL 总数

    def __str__(self) -> str:
        return (f"提交 {self.total} 条 → 成功 {self.success} 条 | "
                f"剩余配额 {self.remain} | 非本站 {self.not_same_site} | 不合法 {self.not_valid}")


@dataclass
class BatchResult:
    """批量推送（异常不中断）的汇总结果。

    errors 记录每个失败分片：[(chunk_urls, BaiduPushError), ...]。
    failed 属性返回失败分片涉及的 URL 总条数。
    """
    success: int = 0
    remain: int = 0
    not_same_site: int = 0
    not_valid: int = 0
    total: int = 0
    errors: list = field(default_factory=list)     # [(chunk_urls, BaiduPushError), ...]

    @property
    def failed(self) -> int:
        return sum(len(ch) for ch, _ in self.errors)

    def __str__(self) -> str:
        s = (f"提交 {self.total} 条 → 成功 {self.success} 条 | "
             f"剩余配额 {self.remain} | 非本站 {self.not_same_site} | 不合法 {self.not_valid}")
        if self.errors:
            s += f" | 失败分片 {len(self.errors)} 个（共 {self.failed} 条）"
        return s


class BaiduPushClient:
    """百度站长平台 URL 主动推送客户端。

    示例：
        client = BaiduPushClient()                 # 使用默认 site/token
        res = client.push(["https://www.chaolei.cc/products.html"])
    """
    def __init__(self,
                 site: str = DEFAULT_SITE,
                 token: str = DEFAULT_TOKEN,
                 timeout: int = 15,
                 max_urls: int = MAX_URLS_PER_POST,
                 user_agent: str = "chaolei-baidu-push/1.0"):
        self.site = _normalize_site(site)
        self.token = token
        if not self.token:
            raise ValueError("百度 token 未配置：请设置环境变量 BAIDU_PUSH_TOKEN（不要在代码中硬编码）")
        self.timeout = timeout
        self.max_urls = max(1, min(max_urls, MAX_URLS_PER_POST))
        self.user_agent = user_agent

    # ---------- 公共接口 ----------
    def push(self, urls: Iterable[str]) -> PushResult:
        """新增推送待收录 URL（action=urls）。"""
        return self._dispatch("urls", urls)

    def update(self, urls: Iterable[str]) -> PushResult:
        """更新已提交 URL（action=update），适用于内容有变更的页面。"""
        return self._dispatch("update", urls)

    def delete(self, urls: Iterable[str]) -> PushResult:
        """删除已提交 URL（action=del），适用于已下线/失效页面。"""
        return self._dispatch("del", urls)

    def push_text(self, text: str) -> PushResult:
        """直接提交「每行一个 URL」的纯文本字符串。"""
        return self.push([line for line in text.splitlines() if line.strip()])

    def push_file(self, path: str) -> PushResult:
        """从文本文件读取 URL（每行一个，# 开头或空行忽略）并提交。"""
        urls = read_url_lines(path)
        return self.push(urls)

    def push_safe(self, urls: Iterable[str], on_error=None) -> BatchResult:
        """批量推送，遇到异常（网络/接口错误）不中断，继续推送剩余分片。

        返回 BatchResult，其 errors 列出每个失败分片 [(urls, BaiduPushError), ...]。
        on_error(chunk_urls, error) 为可选回调，便于实时记录日志。
        """
        cleaned = self._clean(urls)
        if not cleaned:
            raise ValueError("待提交的 URL 列表为空")
        chunks = [cleaned[i:i + self.max_urls]
                  for i in range(0, len(cleaned), self.max_urls)]
        res = BatchResult(total=len(cleaned))
        for chunk in chunks:
            try:
                data = self._post("urls", chunk)
            except BaiduPushError as e:
                res.errors.append((chunk, e))
                if on_error:
                    on_error(chunk, e)
                continue
            res.success += int(data.get("success", 0) or 0)
            if data.get("remain") is not None:
                res.remain = int(data.get("remain"))
            res.not_same_site += int(data.get("not_same_site", 0) or 0)
            res.not_valid += int(data.get("not_valid", 0) or 0)
        return res

    def push_sitemap(self, sitemap_path: str, safe: bool = True):
        """读取 sitemap.xml 中的 URL 并提交。

        safe=True（默认）：异常不中断，返回 BatchResult（含 errors）。
        safe=False：沿用 push() 语义，任一分片失败立即抛出 BaiduPushError。
        """
        urls = read_urls_from_sitemap(sitemap_path)
        return self.push_safe(urls) if safe else self.push(urls)

    # ---------- 内部实现 ----------
    def _dispatch(self, action: str, urls: Iterable[str]) -> PushResult:
        cleaned = self._clean(urls)
        if not cleaned:
            raise ValueError("待提交的 URL 列表为空")
        chunks = [cleaned[i:i + self.max_urls]
                  for i in range(0, len(cleaned), self.max_urls)]
        merged = PushResult(total=len(cleaned))
        for chunk in chunks:
            data = self._post(action, chunk)
            merged.success += int(data.get("success", 0) or 0)
            # remain 取最后一次响应值（配额随提交递减）
            if data.get("remain") is not None:
                merged.remain = int(data.get("remain"))
            merged.not_same_site += int(data.get("not_same_site", 0) or 0)
            merged.not_valid += int(data.get("not_valid", 0) or 0)
        return merged

    def _post(self, action: str, urls: List[str]) -> dict:
        url = f"{API_HOST}/{action}?{urlencode({'site': self.site, 'token': self.token})}"
        body = ("\n".join(urls) + "\n").encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "text/plain;charset=utf-8")
        req.add_header("User-Agent", self.user_agent)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                status = resp.getcode()
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            self._raise_from_response(e.code, raw)
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as e:
            reason = getattr(e, "reason", None) or str(e)
            raise BaiduPushError(f"网络异常，无法连接百度接口：{reason}", code=None, raw=str(e))
        except Exception as e:  # 兜底，避免未预期异常泄露底层堆栈
            raise BaiduPushError(f"请求过程发生未知异常：{e}", code=None, raw=str(e))

        # 解析 JSON 响应
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise BaiduPushError(f"响应不是合法 JSON（HTTP {status}）：{raw[:200]}",
                                 code=status, raw=raw)
        if isinstance(data, dict) and "error" in data:
            self._raise_from_response(data.get("error"), raw, data)
        return data

    @staticmethod
    def _raise_from_response(code, raw: str, data: Optional[dict] = None) -> None:
        msg = None
        if isinstance(data, dict):
            msg = data.get("message")
        if not msg:
            msg = ERROR_MESSAGES.get(code, f"未知错误（HTTP {code}）")
        raise BaiduPushError(msg, code=code, raw=raw)

    @staticmethod
    def _clean(urls: Iterable[str]) -> List[str]:
        seen, out = set(), []
        for u in urls:
            u = (u or "").strip()
            if not u:
                continue
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out


# ---------- 文件 / 输入辅助 ----------
def read_url_lines(path: str) -> List[str]:
    """读取 URL 文本文件，忽略空行与 # 注释行。"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"URL 文件不存在：{path}")
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out


# ---------- sitemap 解析 ----------
def read_urls_from_sitemap(path: str) -> List[str]:
    """解析 sitemap.xml，返回其中所有 <loc> URL。

    支持普通 <urlset>（本地文件）与 <sitemapindex>（自动抓取子 sitemap 并递归解析）。
    子 sitemap 抓取失败仅告警跳过，不影响其余 URL。
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"sitemap 文件不存在：{path}")

    def locs_from_text(text: str) -> List[str]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            raise ValueError(f"sitemap XML 解析失败：{e}")
        tag = root.tag.split("}")[-1]
        out: List[str] = []
        if tag == "sitemapindex":
            subs = [sm.text.strip() for sm in root.iter()
                    if sm.tag.split("}")[-1] == "loc" and sm.text]
            for sub in subs:
                try:
                    with urllib.request.urlopen(sub, timeout=15) as r:
                        out += locs_from_text(r.read().decode("utf-8"))
                except Exception as e:
                    print(f"[warn] 子 sitemap 抓取失败，已跳过：{sub} ({e})", file=sys.stderr)
            return out
        for u in root.iter():
            if u.tag.split("}")[-1] == "loc" and u.text:
                out.append(u.text.strip())
        return out

    return locs_from_text(open(path, encoding="utf-8").read())


# ---------- 命令行入口 ----------
def main():
    ap = argparse.ArgumentParser(description="百度站长平台 URL 主动推送")
    ap.add_argument("--urls", nargs="*", help="命令行直接传入 URL（空格分隔）")
    ap.add_argument("--file", help="从文本文件读取 URL（每行一个，# 开头为注释）")
    ap.add_argument("--sitemap", help="从 sitemap.xml 读取 URL 并提交")
    ap.add_argument("--site", default=DEFAULT_SITE, help="站点域名，默认 %(default)s")
    ap.add_argument("--token", default=DEFAULT_TOKEN, help="百度接口 token（默认读取内嵌/环境变量）")
    ap.add_argument("--action", choices=["urls", "update", "del"], default="urls",
                    help="操作类型：urls=新增推送，update=更新，del=删除")
    ap.add_argument("--safe", dest="safe", action="store_true", default=None,
                    help="异常不中断：某分片失败仍继续推送剩余分片（sitemap 模式默认开启）")
    ap.add_argument("--no-safe", dest="safe", action="store_false",
                    help="（sitemap 模式）逐分片失败即中止")
    ap.add_argument("--timeout", type=int, default=15, help="请求超时秒数")
    args = ap.parse_args()

    client = BaiduPushClient(site=args.site, token=args.token, timeout=args.timeout)

    # ---- sitemap 模式 ----
    if args.sitemap:
        safe = True if args.safe is None else args.safe
        try:
            res = client.push_sitemap(args.sitemap, safe=safe)
        except (BaiduPushError, ValueError, FileNotFoundError) as e:
            print(f"[失败] {e}", file=sys.stderr)
            sys.exit(1)
        print(res)
        if isinstance(res, BatchResult) and res.errors:
            for ch, err in res.errors:
                print(f"  ✗ 分片失败（{len(ch)} 条）: {err.message}（code={err.code}）", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # ---- urls / file / stdin 模式 ----
    urls: List[str] = []
    if args.file:
        urls += read_url_lines(args.file)
    if args.urls:
        urls += [u.strip() for u in args.urls if u.strip()]
    if not urls and not sys.stdin.isatty():        # 管道输入
        urls += [line.strip() for line in sys.stdin if line.strip()]

    if not urls:
        print("没有待推送的 URL。用法见文件顶部 docstring。", file=sys.stderr)
        sys.exit(2)

    if args.safe:
        res = client.push_safe(urls)
        print(res)
        for ch, err in res.errors:
            print(f"  ✗ 分片失败（{len(ch)} 条）: {err.message}（code={err.code}）", file=sys.stderr)
        sys.exit(1 if res.errors else 0)

    try:
        res = client.push(urls) if args.action == "urls" else \
              client.update(urls) if args.action == "update" else \
              client.delete(urls)
    except BaiduPushError as e:
        print(f"[失败] {e.message}（code={e.code}）", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[参数错误] {e}", file=sys.stderr)
        sys.exit(2)

    print(res)
    sys.exit(0)


if __name__ == "__main__":
    main()
