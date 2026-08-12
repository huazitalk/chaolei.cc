/* ============================================================
   潮磊轴承 · 多语言切换引擎 (i18n)
   - 依据 data-i18n / data-i18n-attr 标记切换中英文
   - 偏好存入 localStorage('chaolei_lang')
   - 动态内容(产品弹窗等)通过 window.__t() 取译
   ============================================================ */
(function () {
  'use strict';
  var ZH2EN = window.ZH2EN || {};
  var STORE_KEY = 'chaolei_lang';

  function norm(s) {
    return (s || '').replace(/\s+/g, ' ').replace(/　/g, ' ').trim();
  }
  function tr(zh) {
    var n = norm(zh);
    if (ZH2EN[n] !== undefined) return ZH2EN[n];
    if (ZH2EN[zh] !== undefined) return ZH2EN[zh];
    return zh;
  }
  function curLang() {
    try { return localStorage.getItem(STORE_KEY) || 'zh'; }
    catch (e) { return 'zh'; }
  }
  function saveLang(l) {
    try { localStorage.setItem(STORE_KEY, l); } catch (e) {}
  }

  function applyStatic(lang) {
    var en = (lang === 'en');
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var k = el.getAttribute('data-i18n');
      if (el.__zh === undefined) el.__zh = el.innerHTML;
      el.innerHTML = en ? tr(k) : (el.__zh || el.innerHTML);
    });
    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      var raw = el.getAttribute('data-i18n-attr');
      if (!raw) return;
      var map; try { map = JSON.parse(raw); } catch (e) { return; }
      Object.keys(map).forEach(function (a) {
        if (el.__zhattr === undefined) { el.__zhattr = el.__zhattr || {}; }
        if (el.__zhattr[a] === undefined) el.__zhattr[a] = el.getAttribute(a);
        el.setAttribute(a, en ? tr(map[a]) : (el.__zhattr[a] !== undefined ? el.__zhattr[a] : el.getAttribute(a)));
      });
    });
  }

  function updateSwitch(lang) {
    document.querySelectorAll('.lang-btn').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });
  }
  function updateHtmlLang(lang) {
    document.documentElement.setAttribute('lang', lang === 'en' ? 'en' : 'zh-CN');
  }

  function applyLang(lang, fireEvent) {
    applyStatic(lang);
    updateSwitch(lang);
    updateHtmlLang(lang);
    if (fireEvent !== false) {
      document.dispatchEvent(new CustomEvent('langchange', { detail: { lang: lang } }));
    }
    if (typeof window.__i18nRefresh === 'function') window.__i18nRefresh(lang);
  }

  function setLang(lang) {
    saveLang(lang);
    applyLang(lang);
  }

  // 暴露给动态脚本
  window.__t = function (zh) { return (curLang() === 'en') ? tr(zh) : zh; };
  window.__i18nSetLang = setLang;
  window.__i18nGetLang = curLang;

  function bindSwitch() {
    document.querySelectorAll('.lang-btn').forEach(function (b) {
      b.addEventListener('click', function () {
        setLang(b.getAttribute('data-lang'));
      });
    });
  }

  function init() {
    bindSwitch();
    applyLang(curLang(), false);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
