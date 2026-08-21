# 潮磊轴承官网 · chaolei.cc

馆陶县潮磊轴承制造有限责任公司（品牌「潮磊轴承」）官方网站。
专注微型深沟球轴承（608 系列等）制造 26 年，河北馆陶县源头工厂。

- 线上站点：<https://www.chaolei.cc>
- 部署方式：Cloudflare Pages / Workers（PR 合并到 `main` 后自动拉取部署；`main` 启用 branch protection，**禁止 direct push，必须经 PR 合并**）
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
├── orders/                   # ★ 在线接单模块（纯前端原型，详见下方）
│   ├── index.html             #   订单大厅：列表 / 筛选 / 搜索 / 角色切换
│   ├── publish.html           #   发布订单表单（客户视角）
│   ├── detail.html            #   订单详情：规格 / 状态管理 / 沟通
│   ├── orders.css             #   模块样式（复用站点设计令牌）
│   └── orders.js              #   模块逻辑（localStorage 持久化 + 权限 + 状态流转）
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

## ★ 在线接单模块（orders/）

客户在网站发布微型深沟球轴承采购需求，工厂接单方浏览并接单跟进。覆盖：
**发布订单 → 浏览/承接 → 状态管理 → 双方沟通** 的完整闭环。

> 模块当前为**独立原型**：代码位于 `orders/`，未挂接到主站导航/页脚（首页与联系页不出现入口），可单独预览、独立演进。如需接入主站，再补导航链接即可。

### 业务模型
- **发布方（客户）**：发布轴承采购订单，查看「我的订单」，取消自己的订单。
- **接单方（工厂）**：浏览全部订单，对「待接单」订单接单，推进「进行中 → 已完成」，与发布方沟通。

### 功能清单
| 能力 | 说明 |
|---|---|
| 发布订单 | `publish.html` 表单：系列 / 型号 / 材质 / 数量 / 精度 / 目标价 / 交期 / 用途 / 联系方式，前端校验 |
| 订单大厅 | `index.html`：卡片列表、按角色展示不同动作（工厂见「接单」按钮） |
| 筛选 & 搜索 | 关键词搜索（型号/标题/发布方/公司/单号）+ 状态筛选 + 系列筛选 + 排序 |
| 状态管理 | 待接单 / 进行中 / 已完成 / 已取消 四态流转，带状态进度时间线 |
| 权限控制 | 角色切换演示发布方/接单方权限差异（见下方说明） |
| 沟通渠道 | `detail.html` 内发布方 ↔ 接单方消息气泡，系统消息记录状态变更 |
| 响应式 | 桌面端网格 + 移动端单列，导航折叠菜单，表单/工具栏自适应 |

### 本地预览
```bash
# 从仓库根目录起服务（orders/ 内页面通过 ../ 引用 css/js/img）
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/orders/index.html
```
首次打开会自动写入种子订单（localStorage key：`chaolei_orders_v1`）。
清空演示数据：浏览器控制台执行 `localStorage.clear()` 后刷新。

### ⚠️ 关于「权限控制」的实现说明（重要）
当前为**纯前端原型**，无后端、无真实账号体系：
- 顶部「角色切换」用于**演示权限区分**，不是真实鉴权；数据保存在浏览器本地（localStorage），刷新不丢失，但**不会同步到服务器**，也不具备真实安全性。
- 若要上线为可用系统，需引入后端（如 Cloudflare Workers + D1 / KV）：真实登录会话、服务端权限校验、数据持久化与多端同步、实时沟通（WebSocket / 轮询）。`orders.js` 已按 `data-page` 分派、逻辑与渲染分离，便于后续接入后端 API。

---

## 本地预览与发布

```bash
# 本地起一个静态服务器预览
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/index-markforged.html
```

发布（注意：`main` 有分支保护，禁止 direct push，需走 PR 流程）：

```bash
# 1) 基于 main 切功能分支
git checkout -b feat/online-order
git add -A
git commit -m "feat(orders): 新增在线接单模块（发布/承接/状态/沟通）"

# 2) 推送分支并在 GitHub 发起 PR（合并后 Cloudflare 自动部署到 chaolei.cc）
git push origin feat/online-order
# 浏览器打开 https://github.com/huazitalk/chaolei.cc/compare/main...huazitalk:feat/online-order?expand=1
```

---

## 备注

- `history.html` 为 `noindex` 重定向页，不进入 sitemap，且刻意不带 OG/Twitter/JSON-LD，避免重复内容。
- 全站遵循「无假证书 / 无假案例 / 无假二维码 / 无假视频」的诚实原则，缺失素材以占位或真实素材替代。
