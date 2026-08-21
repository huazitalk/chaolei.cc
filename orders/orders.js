/* ============================================================
   潮磊轴承 · 在线接单模块逻辑引擎（纯前端原型）
   - 数据持久化：localStorage（无后端，演示用）
   - 权限模型：角色切换演示（发布方 / 接单方），非真实鉴权
   - 业务：客户发单 → 工厂接单跟进 → 状态流转 → 沟通
   说明：本文件为零三方依赖的原生 JS，与现有站点 inject_i18n.py 等脚本约定一致。
   ============================================================ */
(function () {
  'use strict';

  /* ----------------------- 常量 ----------------------- */
  var STORAGE_KEY = 'chaolei_orders_v1';
  var ROLE_KEY = 'chaolei_orders_role_v1';
  var CUST_KEY = 'chaolei_orders_customer_v1';

  // 订单状态：待接单 / 进行中 / 已完成 / 已取消
  var STATUS = {
    pending:     { label: '待接单', cls: 'pending' },
    in_progress: { label: '进行中', cls: 'in_progress' },
    completed:   { label: '已完成', cls: 'completed' },
    cancelled:   { label: '已取消', cls: 'cancelled' }
  };
  var STATUS_ORDER = ['pending', 'in_progress', 'completed', 'cancelled'];

  // 轴承系列（用于筛选与表单下拉）
  var CATEGORIES = ['608系列', '627系列', '688系列', '6900系列', '6803系列', '其他微型'];

  // 预设发布方身份（演示多客户视角）
  var CUSTOMERS = ['张经理（东莞玩具厂）', '李工（深圳电机）', '王总（宁波外贸）'];
  var FACTORY_NAME = '潮磊销售-王工';

  /* ----------------------- 工具函数 ----------------------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmt(ts) {
    var d = new Date(ts);
    var p = function (n) { return n < 10 ? '0' + n : n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }
  function genId() {
    var d = new Date();
    var p = function (n) { return n < 10 ? '0' + n : n; };
    return 'ORD-' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + Math.floor(Math.random() * 900 + 100);
  }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function toast(msg) {
    var t = $('#omToast');
    if (!t) { t = document.createElement('div'); t.id = 'omToast'; t.className = 'om-toast'; document.body.appendChild(t); }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.classList.remove('show'); }, 2200);
  }

  /* ----------------------- 存储层 ----------------------- */
  function getOrders() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
    catch (e) { return []; }
  }
  function saveOrders(list) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  }
  function getRole() {
    return localStorage.getItem(ROLE_KEY) === 'factory' ? 'factory' : 'customer';
  }
  function setRole(r) { localStorage.setItem(ROLE_KEY, r); }
  function getCustomer() {
    var c = localStorage.getItem(CUST_KEY);
    return CUSTOMERS.indexOf(c) >= 0 ? c : CUSTOMERS[0];
  }
  function setCustomer(c) { localStorage.setItem(CUST_KEY, c); }

  function findOrder(id) {
    var list = getOrders();
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) return list[i]; }
    return null;
  }
  function updateOrder(id, mutator) {
    var list = getOrders();
    for (var i = 0; i < list.length; i++) {
      if (list[i].id === id) { mutator(list[i]); saveOrders(list); return list[i]; }
    }
    return null;
  }

  /* ----------------------- 种子数据 ----------------------- */
  function seedIfEmpty() {
    if (getOrders().length) return;
    var now = Date.now();
    var H = 3600 * 1000;
    var seed = [
      {
        id: 'ORD-20260821-101', title: '采购 608ZZ 轴承 5000 套', category: '608系列', model: '608ZZ',
        material: '轴承钢', quantity: 5000, unit: '套', precision: 'P0', budget: 0.35,
        deadline: '2026-09-10', usage: '滑板车轮', desc: '用于电动滑板车轮毂，要求转动顺滑、噪音低，可附样品确认。',
        contactName: '张经理', contactPhone: '139****6688', contactCompany: '东莞某玩具厂',
        status: 'pending', publisher: CUSTOMERS[0], taker: null, createdAt: now - 5 * H,
        history: [{ status: 'pending', at: now - 5 * H, by: CUSTOMERS[0] }],
        messages: [{ from: 'customer', name: CUSTOMERS[0], text: '你好，想询一下 608ZZ 5000 套的报价和交期。', at: now - 5 * H }]
      },
      {
        id: 'ORD-20260821-102', title: '采购 608-2RS 轴承 3000 套', category: '608系列', model: '608-2RS',
        material: '轴承钢', quantity: 3000, unit: '套', precision: 'P0', budget: 0.42,
        deadline: '2026-09-05', usage: '电动工具', desc: '小家电电机用，需橡胶密封防油，批量稳定供货。',
        contactName: '李工', contactPhone: '137****2210', contactCompany: '深圳某电机公司',
        status: 'in_progress', publisher: CUSTOMERS[1], taker: FACTORY_NAME, createdAt: now - 28 * H,
        history: [{ status: 'pending', at: now - 28 * H, by: CUSTOMERS[1] }, { status: 'in_progress', at: now - 20 * H, by: FACTORY_NAME }],
        messages: [
          { from: 'customer', name: CUSTOMERS[1], text: '608-2RS 3000 套，麻烦给个最快交期。', at: now - 28 * H },
          { from: 'factory', name: FACTORY_NAME, text: '李工您好，这款现货充足，预计 9 月 5 日前可发，稍后发正式报价单。', at: now - 20 * H },
          { from: 'customer', name: CUSTOMERS[1], text: '好的，麻烦尽快，谢谢！', at: now - 19 * H }
        ]
      },
      {
        id: 'ORD-20260821-103', title: '采购 627 轴承 8000 套', category: '627系列', model: '627',
        material: '碳钢', quantity: 8000, unit: '套', precision: 'P0', budget: 0.18,
        deadline: '2026-09-20', usage: '电动工具/风扇', desc: '成本敏感型订单，碳钢即可，要求尺寸稳定。',
        contactName: '王总', contactPhone: '135****7788', contactCompany: '宁波某外贸公司',
        status: 'pending', publisher: CUSTOMERS[2], taker: null, createdAt: now - 2 * H,
        history: [{ status: 'pending', at: now - 2 * H, by: CUSTOMERS[2] }],
        messages: []
      },
      {
        id: 'ORD-20260821-104', title: '采购 688 轴承 2000 套', category: '688系列', model: '688',
        material: '轴承钢', quantity: 2000, unit: '套', precision: 'P0', budget: 0.25,
        deadline: '2026-08-30', usage: '滑轮/健身器材', desc: '已试样确认，本次为返单。',
        contactName: '张经理', contactPhone: '139****6688', contactCompany: '东莞某玩具厂',
        status: 'completed', publisher: CUSTOMERS[0], taker: FACTORY_NAME, createdAt: now - 72 * H,
        history: [{ status: 'pending', at: now - 72 * H, by: CUSTOMERS[0] }, { status: 'in_progress', at: now - 60 * H, by: FACTORY_NAME }, { status: 'completed', at: now - 40 * H, by: FACTORY_NAME }],
        messages: [
          { from: 'factory', name: FACTORY_NAME, text: '张经理，2000 套已发出，物流单号稍后同步。', at: now - 40 * H },
          { from: 'customer', name: CUSTOMERS[0], text: '收到，辛苦！', at: now - 39 * H }
        ]
      },
      {
        id: 'ORD-20260821-105', title: '采购 6900 轴承 1500 套', category: '6900系列', model: '6900',
        material: '不锈钢', quantity: 1500, unit: '套', precision: 'P6', budget: 0.6,
        deadline: '2026-08-25', usage: '家电电机', desc: '客户临时取消，故撤销。',
        contactName: '李工', contactPhone: '137****2210', contactCompany: '深圳某电机公司',
        status: 'cancelled', publisher: CUSTOMERS[1], taker: null, createdAt: now - 50 * H,
        history: [{ status: 'pending', at: now - 50 * H, by: CUSTOMERS[1] }, { status: 'cancelled', at: now - 46 * H, by: CUSTOMERS[1] }],
        messages: [{ from: 'system', name: '系统', text: '订单已由发布方取消。', at: now - 46 * H }]
      },
      {
        id: 'ORD-20260821-106', title: '采购 608 碳钢轴承 10000 套', category: '608系列', model: '608（碳钢）',
        material: '碳钢', quantity: 10000, unit: '套', precision: 'P0', budget: 0.12,
        deadline: '2026-10-01', usage: '普通玩具', desc: '长期供货需求，先小批试单。',
        contactName: '王总', contactPhone: '135****7788', contactCompany: '宁波某外贸公司',
        status: 'pending', publisher: CUSTOMERS[2], taker: null, createdAt: now - 1 * H,
        history: [{ status: 'pending', at: now - 1 * H, by: CUSTOMERS[2] }],
        messages: []
      },
      {
        id: 'ORD-20260821-107', title: '采购 6803 轴承 4000 套', category: '6803系列', model: '6803',
        material: '轴承钢', quantity: 4000, unit: '套', precision: 'P0', budget: 0.3,
        deadline: '2026-09-15', usage: '汽车部件', desc: '汽车传动小总成用，要求一致性高。',
        contactName: '张经理', contactPhone: '139****6688', contactCompany: '东莞某玩具厂',
        status: 'in_progress', publisher: CUSTOMERS[0], taker: FACTORY_NAME, createdAt: now - 36 * H,
        history: [{ status: 'pending', at: now - 36 * H, by: CUSTOMERS[0] }, { status: 'in_progress', at: now - 30 * H, by: FACTORY_NAME }],
        messages: [{ from: 'factory', name: FACTORY_NAME, text: '张经理，6803 已排产，预计 9 月 15 日前交付。', at: now - 30 * H }]
      }
    ];
    saveOrders(seed);
  }

  /* ----------------------- 权限逻辑（演示级） ----------------------- */
  function partyName() { return getRole() === 'factory' ? FACTORY_NAME : getCustomer(); }

  // 接单方能否接单
  function canTake(o) { return getRole() === 'factory' && o.status === 'pending' && !o.taker; }
  // 接单方能否标记完成
  function canComplete(o) { return getRole() === 'factory' && o.status === 'in_progress' && o.taker === FACTORY_NAME; }
  // 发布方能否取消（仅自己的、未结束订单）
  function canCancelByCustomer(o) { return getRole() === 'customer' && o.publisher === getCustomer() && (o.status === 'pending' || o.status === 'in_progress'); }
  // 接单方能否取消（自己接的、进行中）
  function canCancelByFactory(o) { return getRole() === 'factory' && o.taker === FACTORY_NAME && o.status === 'in_progress'; }
  // 能否沟通（订单存在且未结束）
  function canChat(o) { return o.status === 'pending' || o.status === 'in_progress'; }

  /* ----------------------- 渲染：角色条 ----------------------- */
  function renderRoleBar() {
    var role = getRole();
    $all('[data-role]').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-role') === role);
    });
    var idBox = $('#omIdentity');
    if (idBox) {
      if (role === 'customer') {
        idBox.style.display = '';
        idBox.innerHTML = '<span class="om-rolebar-label">当前发布方：</span>' +
          '<select id="omCustomerSel">' + CUSTOMERS.map(function (c) {
            return '<option value="' + esc(c) + '"' + (c === getCustomer() ? ' selected' : '') + '>' + esc(c) + '</option>';
          }).join('') + '</select>';
        var sel = $('#omCustomerSel');
        sel.addEventListener('change', function () { setCustomer(sel.value); renderCurrentPage(); });
      } else {
        idBox.style.display = '';
        idBox.innerHTML = '<span class="om-rolebar-label">当前接单方：</span><b style="color:#fff;">' + esc(FACTORY_NAME) + '</b>';
      }
    }
    // 工厂视角下隐藏“发布订单”入口（发布是客户动作）
    var pb = $('#omPublishBtn');
    if (pb) pb.style.display = (role === 'customer') ? '' : 'none';
  }

  // 角色切换（所有页面通用）
  function bindRoleSwitch() {
    $all('[data-role]').forEach(function (b) {
      b.addEventListener('click', function () {
        setRole(b.getAttribute('data-role'));
        renderCurrentPage();
      });
    });
  }

  /* ----------------------- 渲染：订单卡片 ----------------------- */
  function cardHtml(o) {
    var st = STATUS[o.status];
    var role = getRole();
    var actions = '';
    if (canTake(o)) {
      actions = '<button class="btn btn-primary btn-sm" data-take="' + esc(o.id) + '">接单</button>';
    }
    actions += '<a class="btn btn-outline btn-sm" href="detail.html?id=' + esc(o.id) + '">查看详情</a>';
    if (role === 'customer' && canCancelByCustomer(o)) {
      actions += '<button class="btn btn-ghost btn-sm" data-cancel="' + esc(o.id) + '">取消</button>';
    }
    var budget = o.budget ? '目标价 ¥' + esc(o.budget) + '/' + esc(o.unit) : '价格面议';
    return '' +
      '<article class="om-card">' +
        '<div class="om-card-top">' +
          '<div>' +
            '<h3 class="om-card-title">' + esc(o.title) + '</h3>' +
            '<div class="om-card-id">' + esc(o.id) + '</div>' +
          '</div>' +
          '<span class="om-badge ' + st.cls + '">' + st.label + '</span>' +
        '</div>' +
        '<div class="om-card-meta">' +
          '<div class="row"><span class="k">型号</span><span class="v">' + esc(o.model) + '</span></div>' +
          '<div class="row"><span class="k">数量</span><span class="v">' + esc(o.quantity) + ' ' + esc(o.unit) + '</span><span class="k" style="min-width:48px;">材质</span><span class="v">' + esc(o.material) + '</span></div>' +
          '<div class="row"><span class="k">预算</span><span class="v">' + esc(budget) + '</span></div>' +
          '<div class="row"><span class="k">交期</span><span class="v">' + esc(o.deadline) + '</span><span class="k" style="min-width:48px;">用途</span><span class="v">' + esc(o.usage) + '</span></div>' +
        '</div>' +
        '<div class="om-card-foot">' +
          '<div class="om-card-pub">发布方：<b>' + esc(o.publisher) + '</b><br>' + fmt(o.createdAt) + '</div>' +
          '<div class="om-card-actions">' + actions + '</div>' +
        '</div>' +
      '</article>';
  }

  /* ----------------------- 列表页 ----------------------- */
  var listState = { search: '', status: 'all', category: 'all', sort: 'new' };

  function visibleOrders() {
    var role = getRole();
    var list = getOrders();
    if (role === 'customer') {
      var c = getCustomer();
      list = list.filter(function (o) { return o.publisher === c; });
    }
    if (listState.status !== 'all') list = list.filter(function (o) { return o.status === listState.status; });
    if (listState.category !== 'all') list = list.filter(function (o) { return o.category === listState.category; });
    if (listState.search) {
      var q = listState.search.toLowerCase();
      list = list.filter(function (o) {
        return (o.title + o.model + o.publisher + o.usage + o.contactCompany + o.id).toLowerCase().indexOf(q) >= 0;
      });
    }
    list.sort(function (a, b) {
      if (listState.sort === 'new') return b.createdAt - a.createdAt;
      if (listState.sort === 'old') return a.createdAt - b.createdAt;
      if (listState.sort === 'qty') return b.quantity - a.quantity;
      return 0;
    });
    return list;
  }

  function renderStats() {
    var box = $('#omStats');
    if (!box) return;
    var role = getRole();
    var list = getRole() === 'customer' ? getOrders().filter(function (o) { return o.publisher === getCustomer(); }) : getOrders();
    var cnt = { pending: 0, in_progress: 0, completed: 0, cancelled: 0 };
    list.forEach(function (o) { cnt[o.status]++; });
    box.innerHTML =
      statCell('s-pending', cnt.pending, '待接单') +
      statCell('s-progress', cnt.in_progress, '进行中') +
      statCell('s-done', cnt.completed, '已完成') +
      statCell('s-cancel', cnt.cancelled, '已取消');
  }
  function statCell(cls, n, t) {
    return '<div class="om-stat ' + cls + '"><div class="n">' + n + '</div><div class="t">' + t + '</div></div>';
  }

  function renderList() {
    var grid = $('#omGrid');
    if (!grid) return;
    var list = visibleOrders();
    if (!list.length) {
      grid.innerHTML = '<div class="om-empty" style="grid-column:1/-1;">' +
        '<div class="ico">📭</div><h3>' + (getRole() === 'customer' ? '您还没有相关订单' : '暂无匹配的订单') + '</h3>' +
        '<p>' + (getRole() === 'customer' ? '点击右上角“发布订单”发布您的轴承采购需求。' : '调整筛选条件，或等待客户发布新需求。') + '</p>' +
        (getRole() === 'customer' ? '<a class="btn btn-primary" href="publish.html">+ 发布订单</a>' : '') +
        '</div>';
      return;
    }
    grid.innerHTML = list.map(cardHtml).join('');
  }

  function bindListEvents() {
    var search = $('#omSearch');
    if (search) search.addEventListener('input', function () { listState.search = search.value.trim(); renderList(); });

    $all('[data-status]').forEach(function (p) {
      p.addEventListener('click', function () {
        listState.status = p.getAttribute('data-status');
        $all('[data-status]').forEach(function (x) { x.classList.toggle('active', x === p); });
        renderList();
      });
    });

    var cat = $('#omCategory');
    if (cat) cat.addEventListener('change', function () { listState.category = cat.value; renderList(); });
    var sort = $('#omSort');
    if (sort) sort.addEventListener('change', function () { listState.sort = sort.value; renderList(); });

    // 接单 / 取消（事件委托）
    var grid = $('#omGrid');
    if (grid) grid.addEventListener('click', function (e) {
      var t = e.target.closest('[data-take],[data-cancel]');
      if (!t) return;
      if (t.hasAttribute('data-take')) takeOrder(t.getAttribute('data-take'));
      else if (t.hasAttribute('data-cancel')) cancelOrder(t.getAttribute('data-cancel'), 'customer');
    });
  }

  function takeOrder(id) {
    if (!canTake(findOrder(id))) { toast('当前角色无接单权限'); return; }
    updateOrder(id, function (o) {
      o.status = 'in_progress'; o.taker = FACTORY_NAME;
      o.history.push({ status: 'in_progress', at: Date.now(), by: FACTORY_NAME });
      o.messages.push({ from: 'system', name: '系统', text: FACTORY_NAME + ' 已接单，订单进入进行中。', at: Date.now() });
    });
    toast('接单成功，订单已进入进行中');
    renderCurrentPage();
  }

  /* ----------------------- 发布页 ----------------------- */
  function bindPublish() {
    var form = $('#omPublishForm');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!validatePublish(form)) return;
      var f = function (n) { return (form.querySelector('[name="' + n + '"]').value || '').trim(); };
      var model = f('model') || '608';
      var qty = parseInt(f('quantity'), 10) || 0;
      var unit = f('unit') || '套';
      var cat = f('category') || '608系列';
      var title = f('title').trim() || (cat + ' ' + model + ' ' + qty + unit + '采购');
      var order = {
        id: genId(),
        title: title,
        category: cat,
        model: model,
        material: f('material') || '轴承钢',
        quantity: qty,
        unit: unit,
        precision: f('precision') || 'P0',
        budget: f('budget') ? parseFloat(f('budget')) : 0,
        deadline: f('deadline') || '待定',
        usage: f('usage') || '通用',
        desc: f('desc'),
        contactName: f('contactName') || getCustomer(),
        contactPhone: f('contactPhone'),
        contactCompany: f('contactCompany'),
        status: 'pending',
        publisher: getCustomer(),
        taker: null,
        createdAt: Date.now(),
        history: [{ status: 'pending', at: Date.now(), by: getCustomer() }],
        messages: []
      };
      var list = getOrders();
      list.unshift(order);
      saveOrders(list);
      toast('订单发布成功');
      setTimeout(function () { location.href = 'detail.html?id=' + encodeURIComponent(order.id); }, 600);
    });
  }

  function validatePublish(form) {
    var ok = true;
    $all('.om-field', form).forEach(function (field) { field.classList.remove('invalid'); });
    function fail(name) {
      var el = form.querySelector('[name="' + name + '"]');
      if (el) { var fld = el.closest('.om-field'); if (fld) fld.classList.add('invalid'); }
      ok = false;
    }
    if (!form.querySelector('[name="model"]').value.trim()) fail('model');
    var q = parseInt(form.querySelector('[name="quantity"]').value, 10);
    if (!q || q <= 0) fail('quantity');
    if (!form.querySelector('[name="deadline"]').value.trim()) fail('deadline');
    if (!form.querySelector('[name="contactName"]').value.trim()) fail('contactName');
    if (!form.querySelector('[name="contactPhone"]').value.trim()) fail('contactPhone');
    if (!ok) toast('请填写带 * 的必填项');
    return ok;
  }

  /* ----------------------- 详情页 ----------------------- */
  function renderDetail() {
    var root = $('#omDetailRoot');
    if (!root) return;
    var id = new URLSearchParams(location.search).get('id');
    var o = id ? findOrder(id) : null;
    if (!o) {
      root.innerHTML = '<div class="om-empty"><div class="ico">🔍</div><h3>未找到该订单</h3><p>订单可能已被删除或链接有误。</p><a class="btn btn-primary" href="index.html">返回订单大厅</a></div>';
      return;
    }
    var st = STATUS[o.status];
    var canTakeNow = canTake(o);
    var canDone = canComplete(o);
    var canCancelC = canCancelByCustomer(o);
    var canCancelF = canCancelByFactory(o);

    // 状态操作按钮
    var actBtns = '';
    if (canTakeNow) actBtns += '<button class="btn btn-primary" data-act="take">接单</button>';
    if (canDone) actBtns += '<button class="btn btn-primary" data-act="complete">标记完成</button>';
    if (canCancelF) actBtns += '<button class="btn btn-ghost" data-act="cancel-factory">取消订单</button>';
    if (canCancelC) actBtns += '<button class="btn btn-ghost" data-act="cancel-customer">取消订单</button>';
    if (!actBtns) actBtns = '<span class="om-rolebar-label" style="color:var(--om-muted);">当前角色下无可用操作</span>';

    var chatLocked = !canChat(o);

    root.innerHTML = '' +
      // 标题区
      '<div style="margin-bottom:18px;">' +
        '<h1 class="om-detail-title">' + esc(o.title) + '</h1>' +
        '<div class="om-detail-sub">' + esc(o.id) + ' · 发布方：' + esc(o.publisher) + (o.taker ? ' · 接单方：' + esc(o.taker) : '') + '</div>' +
      '</div>' +
      '<div class="om-detail-grid">' +
        // 左：规格 + 时间线 + 操作
        '<div>' +
          '<div class="om-panel" style="margin-bottom:18px;">' +
            '<div class="om-panel-head"><h3>订单规格</h3><span class="om-badge ' + st.cls + '">' + st.label + '</span></div>' +
            '<div class="om-panel-body">' + specTable(o) + '</div>' +
          '</div>' +
          '<div class="om-panel" style="margin-bottom:18px;">' +
            '<div class="om-panel-head"><h3>状态进度</h3></div>' +
            '<div class="om-panel-body"><ul class="om-timeline">' + timelineHtml(o) + '</ul></div>' +
          '</div>' +
          '<div class="om-panel">' +
            '<div class="om-panel-head"><h3>订单操作</h3><a class="btn btn-outline btn-sm" href="index.html">返回列表</a></div>' +
            '<div class="om-actions">' + actBtns + '</div>' +
          '</div>' +
        '</div>' +
        // 右：沟通
        '<div class="om-panel">' +
          '<div class="om-chat">' +
            '<div class="om-chat-head"><span class="dot"></span>沟通记录（' + esc(o.publisher) + ' ↔ ' + esc(o.taker || '工厂') + '）</div>' +
            '<div class="om-thread" id="omThread">' + threadHtml(o) + '</div>' +
            (chatLocked
              ? '<div class="om-chat-locked">订单已' + st.label + '，沟通通道已关闭。</div>'
              : '<div class="om-chat-input"><textarea id="omChatText" rows="2" placeholder="输入消息，回车发送（' + esc(partyName()) + '）"></textarea><button class="btn btn-primary" id="omSend">发送</button></div>') +
          '</div>' +
        '</div>' +
      '</div>';

    // 绑定操作
    $all('[data-act]', root).forEach(function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act');
        if (act === 'take') takeOrder(o.id);
        else if (act === 'complete') completeOrder(o.id);
        else if (act === 'cancel-factory') cancelOrder(o.id, 'factory');
        else if (act === 'cancel-customer') cancelOrder(o.id, 'customer');
      });
    });

    // 绑定发送
    var send = $('#omSend');
    if (send) {
      var ta = $('#omChatText');
      function doSend() {
        var text = ta.value.trim();
        if (!text) return;
        updateOrder(o.id, function (od) {
          od.messages.push({ from: getRole() === 'factory' ? 'factory' : 'customer', name: partyName(), text: text, at: Date.now() });
        });
        ta.value = '';
        renderDetail();
        var th = $('#omThread'); if (th) th.scrollTop = th.scrollHeight;
      }
      send.addEventListener('click', doSend);
      ta.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); } });
    }
  }

  function specTable(o) {
    var rows = [
      ['轴承系列', o.category], ['型号', o.model], ['材质', o.material],
      ['数量', o.quantity + ' ' + o.unit], ['精度等级', o.precision],
      ['目标价', o.budget ? '¥' + o.budget + '/' + o.unit : '面议'],
      ['期望交期', o.deadline], ['用途', o.usage],
      ['联系人', o.contactName], ['电话', o.contactPhone],
      ['公司', o.contactCompany || '—'], ['描述', o.desc || '—']
    ];
    return '<table class="om-spec">' + rows.map(function (r) {
      return '<tr><th>' + esc(r[0]) + '</th><td>' + esc(r[1]) + '</td></tr>';
    }).join('') + '</table>';
  }

  function timelineHtml(o) {
    return STATUS_ORDER.map(function (s) {
      var h = null;
      for (var i = 0; i < o.history.length; i++) { if (o.history[i].status === s) h = o.history[i]; }
      if (!h) return '';
      return '<li class="done"><div class="tl-t">' + STATUS[s].label + '</div><div class="tl-d">' + fmt(h.at) + ' · ' + esc(h.by) + '</div></li>';
    }).join('');
  }

  function threadHtml(o) {
    if (!o.messages.length) return '<div style="text-align:center;color:var(--om-muted);padding:24px 0;">暂无沟通记录，接单后即可开始对接。</div>';
    return o.messages.map(function (m) {
      if (m.from === 'system') return '<div class="om-msg system"><div class="bubble">' + esc(m.text) + '</div></div>';
      return '<div class="om-msg ' + m.from + '"><div class="bubble">' + esc(m.text) + '</div><div class="meta">' + esc(m.name) + ' · ' + fmt(m.at) + '</div></div>';
    }).join('');
  }

  function completeOrder(id) {
    if (!canComplete(findOrder(id))) { toast('当前角色无法标记完成'); return; }
    updateOrder(id, function (o) {
      o.status = 'completed';
      o.history.push({ status: 'completed', at: Date.now(), by: FACTORY_NAME });
      o.messages.push({ from: 'system', name: '系统', text: '订单已标记为完成。', at: Date.now() });
    });
    toast('订单已标记完成');
    renderDetail();
  }

  function cancelOrder(id, by) {
    var o = findOrder(id);
    if (!o) return;
    var allowed = by === 'factory' ? canCancelByFactory(o) : canCancelByCustomer(o);
    if (!allowed) { toast('当前角色无权取消该订单'); return; }
    updateOrder(id, function (od) {
      od.status = 'cancelled';
      od.history.push({ status: 'cancelled', at: Date.now(), by: partyName() });
      od.messages.push({ from: 'system', name: '系统', text: '订单已取消（操作方：' + partyName() + '）。', at: Date.now() });
    });
    toast('订单已取消');
    renderCurrentPage();
  }

  /* ----------------------- 页面分派 ----------------------- */
  function renderCurrentPage() {
    renderRoleBar();
    var page = document.body.getAttribute('data-page');
    if (page === 'list') { renderStats(); renderList(); }
    else if (page === 'detail') { renderDetail(); }
  }

  function init() {
    seedIfEmpty();
    bindRoleSwitch();
    var page = document.body.getAttribute('data-page');
    if (page === 'list') { bindListEvents(); renderCurrentPage(); }
    else if (page === 'publish') { bindPublish(); renderRoleBar(); }
    else if (page === 'detail') { renderCurrentPage(); }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
