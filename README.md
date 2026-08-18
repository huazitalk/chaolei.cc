# 潮磊轴承官网 · chaolei.cc

馆陶县潮磊轴承制造有限责任公司（品牌「潮磊轴承」）官方网站。
专注微型深沟球轴承（608 系列等）制造 26 年，河北馆陶县源头工厂。

- 线上站点：<https://www.chaolei.cc>
- 部署方式：GitHub Pages（推送 `main` 分支自动构建发布，见 `.github/workflows/deploy.yml`）
- 技术栈：纯静态 HTML + 内联 CSS/JS，无外部前端框架；深钢蓝 `#0E2A47` + 橙 `#E8590C`

---

## 目录结构

```
.
├── index.html                # 官网首页
├── index-markforged.html     # Markforged 工业风格首页（部署入口，chaolei.cc 实际落地页）
├── about.html                # 关于我们（含发展历程）
├── products.html             # 608 系列微型轴承产品中心
├── applications.html         # 应用方案（玩具 / 电动工具 / 小家电电机等）
├── capabilities.html         # 制造能力（磨床 / 超精机 / 合套仪）
├── contact.html              # 联系方式（电话 13168867664）
├── history.html              # 发展历程重定向页（noindex，跳转到 about.html#development-history）
├── robots.txt / sitemap.xml  # SEO/GEO 基础文件
├── css/  js/  img/  video/   # 资源
├── meta-config.json          # ★ 页面元信息单一事实来源（<title> / <meta name="description">）
└── scripts/                  # 站点构建 / SEO 工具（随仓库发布）
    ├── manage_meta.py          # ★ 元信息集中注入脚本（本文档重点）
    ├── verify_seo_geo.py       # SEO/GEO 一致性校验（含 META 维度）
    ├── baidu_push.py           # 百度站长平台主动推送
    └── inject_baidu_autopush.py# 页面百度自动推送片段注入
```

> `scripts/` 目录会随仓库一起发布到 GitHub Pages（既有约定）。其中不含任何密钥，
> 百度推送 token 通过 GitHub Actions Secrets（`BAIDU_PUSH_TOKEN`）注入。

---

## ★ 页面元信息集中管理（本次新增）

把散落在 8 个 HTML 里的 `<title>` 与 `<meta name="description">` 收敛为
**单一事实来源 + 可重复注入**，确保搜索引擎 / AI 爬虫直接抓到正确的页面摘要。

### 单一事实来源：`meta-config.json`

```jsonc
{
  "default": {
    "title": "潮磊轴承 - 26年微型深沟球轴承源头工厂 | 608系列 | 河北馆陶",
    "description": "馆陶县潮磊轴承制造有限责任公司，成立于2000年……支持定制。"
  },
  "pages": {
    "index.html":        { "title": null, "description": null },   // null = 继承 default
    "about.html":        { "title": "关于潮磊轴承 | …", "description": "…" },
    // …… 其余逐页可覆盖；首页两个入口文件继承 default
  }
}
```

- `default` 作为站点级兜底；`pages.<file>` 逐页覆盖。
- 值为 `null` 或缺失 → 自动继承 `default`（全站统一只需把所有页改 `null`）。

### 注入 / 管理：`scripts/manage_meta.py`

```bash
# 依赖：Python 3（manage_meta.py 需要 beautifulsoup4）
pip install beautifulsoup4

# 按配置注入 / 更新全部页面（脚本会自动定位仓库根目录）
python3 scripts/manage_meta.py

# 仅校验差异，不写文件（dry-run）
python3 scripts/manage_meta.py --check

# 也可显式指定站点目录 / 配置文件
python3 scripts/manage_meta.py --dir . --config meta-config.json
```

脚本保证每个 `<head>` 内 `<title>` 与 `<meta name="description">` **唯一**，
并同步 i18n 属性（`data-i18n` / `data-i18n-attr`），中英双语切换不受影响。

### 一致性校验：`scripts/verify_seo_geo.py`

```bash
# 离线检查本地文件（canonical / JSON-LD / sitemap / robots / META 等）
python3 scripts/verify_seo_geo.py

# 额外联网比对远程仓库 + 线上抓取（需能访问 github.com / chaolei.cc）
python3 scripts/verify_seo_geo.py --live
```

`--- META ---` 段落会校验每页 title / description 的唯一性、非空与合理长度。

---

## 本地预览与发布

```bash
# 本地起一个静态服务器预览
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/index-markforged.html
```

发布即推送到 `main`：

```bash
git add -A
git commit -m "feat: …"
git push origin main        # 触发 .github/workflows/deploy.yml 自动部署到 GitHub Pages
```

---

## 备注

- `history.html` 为 `noindex` 重定向页，不进入 sitemap，且刻意不带 OG/Twitter/JSON-LD，避免重复内容。
- 全站遵循「无假证书 / 无假案例 / 无假二维码 / 无假视频」的诚实原则，缺失素材以占位或真实素材替代。
