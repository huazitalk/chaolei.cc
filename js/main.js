/* ============================================
   潮磊轴承官网 · 交互脚本
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {
  let currentDetailId = null;

  // ---- Mobile Nav Toggle ----
  const toggle = document.getElementById('mobileToggle');
  const mobileNav = document.getElementById('mobileNav');

  if (toggle && mobileNav) {
    toggle.addEventListener('click', function () {
      mobileNav.classList.toggle('open');
      toggle.classList.toggle('active');
    });

    // Close on link click
    mobileNav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        mobileNav.classList.remove('open');
        toggle.classList.remove('active');
      });
    });
  }

  // ---- Header Scroll Effect ----
  const header = document.getElementById('header');
  if (header) {
    let lastScroll = 0;
    window.addEventListener('scroll', function () {
      const scrollY = window.scrollY || window.pageYOffset;
      if (scrollY > 20) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
      lastScroll = scrollY;
    }, { passive: true });
  }

  // ---- Smooth scroll for anchor links ----
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const offsetTop = target.getBoundingClientRect().top + window.pageYOffset - 90;
        window.scrollTo({ top: offsetTop, behavior: 'smooth' });
      }
    });
  });

  // ---- Stats number animation on scroll ----
  const statNumbers = document.querySelectorAll('.stat-number');
  if (statNumbers.length > 0) {
    const observerOptions = { threshold: 0.3, rootMargin: '0px' };
    const statsObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          statsObserver.unobserve(entry.target);
        }
      });
    }, observerOptions);

    statNumbers.forEach(function (num) {
      num.style.opacity = '0';
      num.style.transform = 'translateY(16px)';
      num.style.transition = 'opacity .5s ease, transform .5s ease';
      statsObserver.observe(num);
    });
  }

  // ---- Workshop video controls ----
  document.querySelectorAll('.video-frame').forEach(function (frame) {
    var video = frame.querySelector('.workshop-video');
    var playBtn = frame.querySelector('.video-play-btn');
    var muteBtn = frame.querySelector('.video-mute-btn');
    if (!video) return;
    var playIcon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
    var pauseIcon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>';
    var muteIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
    var soundIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 010 7M19 5a9 9 0 010 14"/></svg>';

    video.addEventListener('play', function () {
      frame.classList.remove('paused');
      if (playBtn) playBtn.innerHTML = pauseIcon;
    });
    video.addEventListener('pause', function () {
      frame.classList.add('paused');
      if (playBtn) playBtn.innerHTML = playIcon;
    });

    if (playBtn) {
      playBtn.addEventListener('click', function () {
        if (video.paused) { var p = video.play(); if (p && p.catch) p.catch(function(){}); }
        else { video.pause(); }
      });
    }
    if (muteBtn) {
      muteBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        video.muted = !video.muted;
        muteBtn.innerHTML = video.muted ? muteIcon : soundIcon;
      });
    }
    // 改为点击播放：不自动播放，仅保留 play/pause 切换
  });

  // ---- Card hover lift effect enhancement ----
  const cards = document.querySelectorAll('.card, .badge-card, .contact-card, .stat-card');
  cards.forEach(function (card) {
    card.addEventListener('mouseenter', function () {
      this.style.transition = 'all .3s cubic-bezier(.25,.46,.45,.94)';
    });
  });

  // ---- Product inquiry & spec modals ----
  // 通用轴承参数生成器（材质/密封等均为厂内可选配置，非虚构具体载荷数值）
  function bearingParams(d, D, B, type, material, app) {
    return [
      ['轴承类型', type],
      ['内径 d', d + ' mm'],
      ['外径 D', D + ' mm'],
      ['宽度 B', B + ' mm'],
      ['可选材质', material],
      ['保持架', '冲压钢板 / 尼龙（可选）'],
      ['密封形式', 'ZZ 防尘盖 / 2RS 橡胶密封 / 开放式'],
      ['精度等级', 'P0（可选 P6）'],
      ['游隙组别', 'C0（可选 C2 / C3）'],
      ['润滑方式', '防尘脂 / 油润滑（可选）'],
      ['典型应用', app],
      ['定制说明', '支持非标尺寸、材质、密封定制']
    ];
  }

  const PRODUCTS = {
    '608-bxg': { name: '608 轴承钢', spec: '8×22×7 mm', cat: '608 旗舰系列', params: bearingParams(8, 22, 7, '深沟球轴承（微型）', 'GCr15 轴承钢（默认）', '滑板车轮、电机、高载荷场景') },
    '608-tg': { name: '608 碳钢', spec: '8×22×7 mm', cat: '608 旗舰系列', params: bearingParams(8, 22, 7, '深沟球轴承（微型）', '优质碳钢（可选轴承钢 / 不锈钢）', '普通玩具、指尖陀螺等轻载荷低转速') },
    '608-dt1': { name: '608 单凸一', spec: '8×22×7 mm · 单面凸缘', cat: '608 旗舰系列', params: [
      ['轴承类型', '深沟球轴承（单面凸缘）'], ['内径 d', '8 mm'], ['外径 D', '22 mm'], ['宽度 B', '7 mm'],
      ['凸缘结构', '单面凸缘（卡簧固定 / 轴向定位）'], ['可选材质', '碳钢 / GCr15 轴承钢'],
      ['保持架', '冲压钢板 / 尼龙（可选）'], ['密封形式', 'ZZ / 2RS / 开放式'], ['精度等级', 'P0（可选 P6）'],
      ['典型应用', '卡簧固定、轴向定位安装'], ['定制说明', '支持非标尺寸、材质、密封定制'] ] },
    '608-dt2': { name: '608 单凸二', spec: '8×22×7 mm · 单面凸缘', cat: '608 旗舰系列', params: [
      ['轴承类型', '深沟球轴承（单面凸缘）'], ['内径 d', '8 mm'], ['外径 D', '22 mm'], ['宽度 B', '7 mm'],
      ['凸缘结构', '单面凸缘（另一种规格变体）'], ['可选材质', '碳钢 / GCr15 轴承钢'],
      ['保持架', '冲压钢板 / 尼龙（可选）'], ['密封形式', 'ZZ / 2RS / 开放式'], ['精度等级', 'P0（可选 P6）'],
      ['典型应用', '不同安装孔位与卡簧尺寸需求'], ['定制说明', '支持非标尺寸、材质、密封定制'] ] },
    '608-st1': { name: '608 双凸一', spec: '8×22×7 mm · 双面凸缘', cat: '608 旗舰系列', params: [
      ['轴承类型', '深沟球轴承（双面凸缘）'], ['内径 d', '8 mm'], ['外径 D', '22 mm'], ['宽度 B', '7 mm'],
      ['凸缘结构', '双面凸缘（防止双向轴向窜动）'], ['可选材质', '碳钢 / GCr15 轴承钢'],
      ['保持架', '冲压钢板 / 尼龙（可选）'], ['密封形式', 'ZZ / 2RS / 开放式'], ['精度等级', 'P0（可选 P6）'],
      ['典型应用', '精密传动机构、定位轴承'], ['定制说明', '支持非标尺寸、材质、密封定制'] ] },
    '626': { name: '626', spec: '6×19×6 mm', cat: '微型深沟球轴承', params: bearingParams(6, 19, 6, '微型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '遥控车、小马达') },
    '607': { name: '607', spec: '7×19×6 mm', cat: '微型深沟球轴承', params: bearingParams(7, 19, 6, '微型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '航模、小家电') },
    '698': { name: '698', spec: '8×19×6 mm', cat: '微型深沟球轴承', params: bearingParams(8, 19, 6, '微型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '轮滑、健身器材') },
    '627': { name: '627', spec: '7×22×7 mm', cat: '微型深沟球轴承', params: bearingParams(7, 22, 7, '微型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '电动工具、风扇') },
    '696': { name: '696', spec: '6×15×5 mm', cat: '微型深沟球轴承', params: bearingParams(6, 15, 5, '微型薄壁轴承', '碳钢（可选轴承钢 / 不锈钢）', '指尖陀螺、微型电机') },
    '6800': { name: '6800', spec: '10×19×5 mm', cat: '小型深沟球轴承', params: bearingParams(10, 19, 5, '小型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '精密仪器、机器人') },
    '688': { name: '688', spec: '8×16×5 mm', cat: '微型深沟球轴承', params: bearingParams(8, 16, 5, '微型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '滑轮、微型传动') },
    '687': { name: '687', spec: '7×14×5 mm', cat: '微型深沟球轴承', params: bearingParams(7, 14, 5, '微型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '航模、小家电') },
    '689': { name: '689', spec: '9×17×5 mm', cat: '微型深沟球轴承', params: bearingParams(9, 17, 5, '微型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '微型电机、仪器') },
    '6803': { name: '6803', spec: '17×26×5 mm', cat: '小型深沟球轴承', params: bearingParams(17, 26, 5, '小型薄壁轴承', '碳钢（可选轴承钢 / 不锈钢）', '汽车部件、传动') },
    '6900': { name: '6900', spec: '10×22×6 mm', cat: '小型深沟球轴承', params: bearingParams(10, 22, 6, '小型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '家电电机、泵') },
    '6901': { name: '6901', spec: '12×24×6 mm', cat: '小型深沟球轴承', params: bearingParams(12, 24, 6, '小型深沟球轴承', '碳钢（可选轴承钢 / 不锈钢）', '汽车、工业传动') }
  };

  const paramModal = document.getElementById('paramModal');
  const qrModal = document.getElementById('qrModal');

  function openModal(m) { if (!m) return; m.classList.add('open'); document.body.style.overflow = 'hidden'; }
  function closeModal(m) { if (!m) return; m.classList.remove('open'); document.body.style.overflow = ''; }

  function openParam(btn) {
    const id = btn.getAttribute('data-product');
    const p = PRODUCTS[id];
    if (!p) return;
    // 读取卡片原有基础信息，确保弹窗内信息不丢失
    const card = btn.closest('.product-card');
    const figEl = document.getElementById('paramFigure');
    const tagsEl = document.getElementById('paramTags');
    const descEl = document.getElementById('paramDesc');

    if (card) {
      const imgEl = card.querySelector('.product-img');
      if (imgEl) {
        const raw = imgEl.innerHTML.trim();
        if (/<img/i.test(raw)) {
          figEl.innerHTML = raw;                 // 真实产品图
        } else {
          figEl.innerHTML = '<span class="param-figure-icon">' + (raw || '⚙️') + '</span>';
        }
      }
      const trowEl = card.querySelector('.tag-row');
      if (trowEl && trowEl.children.length) {
        tagsEl.innerHTML = trowEl.innerHTML;
        tagsEl.style.display = '';
      } else {
        tagsEl.innerHTML = ''; tagsEl.style.display = 'none';
      }
      const pEl = card.querySelector('p');
      descEl.textContent = pEl ? pEl.textContent.trim() : '';
    } else {
      figEl.innerHTML = '<span class="param-figure-icon">⚙️</span>';
      tagsEl.innerHTML = ''; tagsEl.style.display = 'none';
      descEl.textContent = '';
    }

    document.getElementById('paramTitle').textContent = window.__t(p.name);
    document.getElementById('paramSpec').textContent = window.__t(p.spec) + ' · ' + window.__t(p.cat);
    document.getElementById('paramBody').innerHTML = p.params
      .map(function (r) { return '<tr><td>' + window.__t(r[0]) + '</td><td>' + window.__t(r[1]) + '</td></tr>'; })
      .join('');
    currentDetailId = id;
    openModal(paramModal);
  }

  document.querySelectorAll('.p-btn--inquire').forEach(function (b) {
    b.addEventListener('click', function () { openModal(qrModal); });
  });
  document.querySelectorAll('.p-btn--detail').forEach(function (b) {
    b.addEventListener('click', function () { openParam(b); });
  });

  [paramModal, qrModal].forEach(function (m) {
    if (!m) return;
    m.addEventListener('click', function (e) { if (e.target === m) closeModal(m); });
    const closeBtn = m.querySelector('.modal-close');
    if (closeBtn) closeBtn.addEventListener('click', function () { closeModal(m); });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeModal(paramModal); closeModal(qrModal); }
  });

  // 语言切换时，若参数弹窗处于打开状态则重新渲染（确保动态内容同步翻译）
  window.__i18nRefresh = function () {
    if (currentDetailId && paramModal && paramModal.classList.contains('open')) {
      const btn = document.querySelector('.p-btn--detail[data-product="' + currentDetailId + '"]');
      if (btn) openParam(btn);
    }
  };

});
