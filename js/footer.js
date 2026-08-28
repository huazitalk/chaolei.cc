/* ============================================================
   潮磊轴承 · 统一页脚 (single source of truth)
   - 全站底部通栏复用同一套内容配置 (取自 contact.html 的 footer)
   - 注入后重新应用 i18n，保持与全站中英文切换一致
   ============================================================ */
(function () {
  'use strict';

  var FOOTER_HTML = '<footer class="footer">\n' +
    '<div class="container">\n' +
    '<div class="footer-grid">\n' +
    '<div class="footer-brand"><span class="logo-text"><span data-i18n="潮磊">潮磊</span><span><span data-i18n="轴承">轴承</span></span></span><p class="footer-legal" style="color:#fff;font-size:15px;font-weight:700;margin:4px 0 14px;letter-spacing:.5px;"><span data-i18n="馆陶县潮磊轴承制造有限责任公司">馆陶县潮磊轴承制造有限责任公司</span></p><p><span data-i18n="26 年专注微型深沟球轴承制造。">26 年专注微型深沟球轴承制造。</span><br/><span data-i18n="精密 · 稳定 · 长期主义。">精密 · 稳定 · 长期主义。</span></p></div>\n' +
    '<div class="footer-col"><h4><span data-i18n="产品 Products">产品 Products</span></h4><a href="products.html"><span data-i18n="深沟球轴承">深沟球轴承</span></a><a href="products.html"><span data-i18n="608 系列">608 系列</span></a><a href="products.html"><span data-i18n="微型轴承">微型轴承</span></a><a href="products.html"><span data-i18n="非标定制">非标定制</span></a></div>\n' +
    '<div class="footer-col"><h4><span data-i18n="应用 Applications">应用 Applications</span></h4><a href="applications.html"><span data-i18n="电动工具">电动工具</span></a><a href="applications.html"><span data-i18n="家电电机">家电电机</span></a><a href="applications.html"><span data-i18n="滑板/健身器材">滑板/健身器材</span></a><a href="applications.html"><span data-i18n="出口市场">出口市场</span></a></div>\n' +
    '<div class="footer-col"><h4><span data-i18n="公司 Company">公司 Company</span></h4><a href="about.html"><span data-i18n="关于潮磊">关于潮磊</span></a><a href="history.html"><span data-i18n="发展历程">发展历程</span></a><a href="capabilities.html"><span data-i18n="生产能力">生产能力</span></a><a href="contact.html"><span data-i18n="联系我们">联系我们</span></a></div>\n' +
    '<div class="footer-col footer-contact"><h4><span data-i18n="联系 Contact">联系 Contact</span></h4>\n' +
    
    '<p><span data-i18n="💬 微信：xingzhitalk">💬 微信：xingzhitalk</span></p>\n' +
    '<p class="footer-contact-line"><span>𝕏</span> <a href="https://x.com/chaoleihb" rel="noopener" style="color:var(--accent);" target="_blank">@chaoleihb</a></p>\n' +
    '<p><span data-i18n="📍 中国河北省邯郸市馆陶县魏僧寨镇杨草厂村">📍 中国河北省邯郸市馆陶县魏僧寨镇杨草厂村</span></p></div>\n' +
    '</div>\n' +
    '<div class="footer-bottom"><span><span data-i18n="© 2026 潮磊轴承 版权所有">© 2026 潮磊轴承 版权所有</span></span><span><span data-i18n="26 年微型深沟球轴承专业制造商">26 年微型深沟球轴承专业制造商</span></span></div>\n' +
    '</div>\n' +
    '</footer>';

  function render() {
    var ph = document.getElementById('siteFooter');
    if (!ph) return;
    ph.innerHTML = FOOTER_HTML;
    // 重新应用 i18n（含刚注入的页脚），保持与全站翻译一致
    if (typeof window.__i18nSetLang === 'function' && typeof window.__i18nGetLang === 'function') {
      try { window.__i18nSetLang(window.__i18nGetLang()); } catch (e) {}
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
