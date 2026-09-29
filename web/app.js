// 首页：全部内容从 window.D 渲染。数据是原文，一律用 textContent / createElement，不拼 innerHTML。
(function () {
  'use strict';
  var D = window.D || [];
  var CHAT = '(chat)', GENERAL = '(普通对话)', NOTOPIC = '(未分类)', LIMIT = 30;
  // 来源：键、全称、短名。ChatGPT 存档是独立页面（数据里只有 gpt）：来源筛选、图表、图例都只列 gpt；Claude 页照旧 cc + ai。
  var SRC = { cc: ['Claude Code', 'Code'], ai: ['claude.ai', 'Chat'], gpt: ['ChatGPT', 'GPT'] };
  var GPT = D.some(function (d) { return d.src === 'gpt'; });
  var ACT = GPT ? ['gpt'] : ['cc', 'ai'];   // 图表里画哪几个来源（堆叠顺序）
  var PSRC = GPT ? 'gpt' : 'cc';            // 哪个来源的 _pk 是“项目”
  var WEEK = ['一', '二', '三', '四', '五', '六', '日'];
  var SVGNS = 'http://www.w3.org/2000/svg';

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function svg(tag, attrs, text) {
    var e = document.createElementNS(SVGNS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  }
  function store(k, v) {
    try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {}
    return null;
  }

  // ---------- 预处理 ----------
  // 项目文件夹名拆成 [日期, 名字]：260101_demo、260101报告、my-app-260101（6 位日期在开头或结尾）
  function projParts(k) {
    if (k === CHAT) return ['', 'claude.ai 对话'];
    if (k === GENERAL) return ['', '普通对话'];
    if (/^GPT /.test(k)) return ['', k];   // 自定义 GPT：'GPT g-xxxx'，别把 id 末尾的数字当日期
    if (/^(\/home\/[^\/]+|\/Users\/[^\/]+|[A-Za-z]:[\\\/]Users[\\\/][^\\\/]+)[\\\/]?$/.test(k)) return ['', '主目录'];
    var s = k.split(/[\\\/]/).filter(Boolean).pop() || k, m;
    if ((m = /^(\d{6})[_\- ]?(.+)$/.exec(s))) return [m[1], m[2]];
    if ((m = /^(.+?)[_\- ](\d{6})$/.exec(s))) return [m[2], m[1]];
    return ['', s];
  }
  function projName(k) { var p = projParts(k); return p[0] ? p[0] + ' ' + p[1] : p[1]; }
  function projInto(box, k) {  // 灰色等宽日期 + 正常字名字
    var p = projParts(k);
    if (!p[0]) { box.appendChild(document.createTextNode(p[1])); return box; }
    box.appendChild(el('span', 'pd', p[0]));
    box.appendChild(document.createTextNode(' '));  // 放不下时先在日期后折行，名字整体换到下一行
    box.appendChild(el('span', 'pn', p[1]));
    return box;
  }
  function cut(s, n) { return s.length > n ? s.slice(0, n) + '…' : s; }
  function summary(d) {
    if (d.sum) return d.sum;
    if (d.q && d.q.length) return d.q.slice(0, 3).join(' · ');
    if (d.as) return cut(d.as.replace(/\*\*Conversation Overview\*\*/i, '').replace(/[*#`>_]+/g, '').replace(/\s+/g, ' ').trim(), 60);
    return '';
  }
  var maxLast = '';
  D.forEach(function (d) {
    d._pk = d.src === 'ai' ? CHAT : d.src === 'gpt' ? (d.proj || GENERAL) : (d.proj || '(未记录项目)');
    d._tp = d.topics && d.topics.length ? d.topics : null;
    d._last = d.end || d.start || '';
    d._sum = summary(d);
    d._txt = [d.t, (d.q || []).join(' '), d.sum || '', d.as || '', (d.topics || []).join(' ')].join('\n').toLowerCase();
    if (d._last > maxLast) maxLast = d._last;
  });
  var CUR_YEAR = maxLast.slice(0, 4);
  function when(s) { return s.slice(0, 4) === CUR_YEAR ? s.slice(5, 16) : s.slice(0, 10); }

  // 全量数据的项目 / 主题清单（侧栏顺序固定，不随筛选跳动）
  function tally(keyOf) {
    var c = {};
    D.forEach(function (d) { keyOf(d).forEach(function (k) { c[k] = (c[k] || 0) + 1; }); });
    return Object.keys(c).sort(function (a, b) { return c[b] - c[a]; });
  }
  var PROJS = tally(function (d) { return d.src === PSRC ? [d._pk] : []; });
  var TOPICS = tally(function (d) { return d._tp || []; });
  var HAS_UNTAGGED = TOPICS.length && D.some(function (d) { return !d._tp; });

  // ---------- 状态 ----------
  var st = {
    src: 'all', proj: null, topic: null, month: null, star: false, q: '',
    group: store('group') || 'proj', sort: store('sort') || 'recent', metric: store('metric') || 'n'
  };
  if (!/^(proj|topic|month)$/.test(st.group)) st.group = 'proj';
  if (!/^(recent|nq|nmsg)$/.test(st.sort)) st.sort = 'recent';
  if (!/^(n|nq)$/.test(st.metric)) st.metric = 'n';
  var collapsed = {};
  try { collapsed = JSON.parse(store('collapsed') || '{}') || {}; } catch (e) {}
  var expanded = {};

  function ok(d, skip) {
    if (skip !== 'src' && st.src !== 'all' && d.src !== st.src) return false;
    if (skip !== 'proj' && st.proj && d._pk !== st.proj) return false;
    if (skip !== 'topic' && st.topic &&
        (st.topic === NOTOPIC ? d._tp : !(d._tp && d._tp.indexOf(st.topic) >= 0))) return false;
    if (skip !== 'month' && st.month && d.start.slice(0, 7) !== st.month) return false;
    if (skip !== 'star' && st.star && !d.star) return false;
    if (skip !== 'q' && st.q && d._txt.indexOf(st.q) < 0) return false;
    return true;
  }
  function count(skip, keyOf) {
    var c = {};
    D.forEach(function (d) { if (ok(d, skip)) keyOf(d).forEach(function (k) { c[k] = (c[k] || 0) + 1; }); });
    return c;
  }

  // ---------- 侧栏 ----------
  function facet(box, items, cur, set) {
    var a = document.activeElement, fk = a && box.contains(a) ? a.getAttribute('data-k') : null;
    box.textContent = '';
    items.forEach(function (it) {
      var b = el('button', 'fi' + (it.n ? '' : ' zero'));
      b.type = 'button';
      b.setAttribute('data-k', it.key);
      b.setAttribute('aria-pressed', String(it.key === cur));
      if (it.title) b.title = it.title;
      if (it.dot) b.appendChild(el('i', 'sw ' + it.dot));
      b.appendChild(it.proj ? projInto(el('span', 'fl'), it.key) : el('span', 'fl', it.label));
      b.appendChild(el('span', 'fn', String(it.n || 0)));
      b.addEventListener('click', function () { set(it.key === cur ? null : it.key); render(); });
      box.appendChild(b);
      if (it.key === fk) b.focus();
    });
  }
  function renderSide() {
    var cs = count('src', function (d) { return ['all', d.src]; });
    facet($('f-src'), (GPT ? [] : [{ key: 'all', label: '全部', n: cs.all }]).concat(ACT.map(function (k) {
      return { key: k, label: SRC[k][0], n: cs[k], dot: k };
    })), st.src, function (k) { st.src = k || 'all'; });

    var cst = count('star', function (d) { return d.star ? ['y'] : []; });
    facet($('f-star'), [{ key: 'y', label: '★ 只看星标', n: cst.y }], st.star ? 'y' : null,
      function (k) { st.star = !!k; });

    var cp = count('proj', function (d) { return [d._pk]; });
    facet($('f-proj'), PROJS.concat(GPT ? [] : [CHAT]).map(function (k) {
      return { key: k, proj: 1, n: cp[k], title: k === CHAT ? 'claude.ai 网页对话（没有项目文件夹）' : k === GENERAL ? '没有指定自定义 GPT 的普通对话' : k, dot: k === CHAT ? 'ai' : null };
    }), st.proj, function (k) { st.proj = k; });

    var box = $('f-topic');
    if (!TOPICS.length) { box.textContent = ''; box.appendChild(el('p', 'side-note', '还没有主题标签。打完标签后这里会列出每个主题。')); return; }
    var ct = count('topic', function (d) { return d._tp || [NOTOPIC]; });
    facet(box, TOPICS.concat(HAS_UNTAGGED ? [NOTOPIC] : []).map(function (k) {
      return { key: k, label: k === NOTOPIC ? '未分类' : k, n: ct[k] };
    }), st.topic, function (k) { st.topic = k; });
  }

  // ---------- 统计卡 ----------
  function dayNum(s) { return Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / 864e5; }
  function renderTiles(L) {
    var nq = 0, ns = {}, days = {}, pc = {}, tc = {}, first = '', last = '';
    L.forEach(function (d) {
      nq += d.nq || 0;
      ns[d.src] = (ns[d.src] || 0) + 1;
      if (d.src === PSRC) pc[d._pk] = (pc[d._pk] || 0) + 1;
      days[d.start.slice(0, 10)] = 1;
      (d._tp || []).forEach(function (t) { tc[t] = (tc[t] || 0) + 1; });
      if (!first || d.start < first) first = d.start;
      if (d._last > last) last = d._last;
    });
    function top(c) { var k = null; for (var x in c) if (k === null || c[x] > c[k]) k = x; return k; }
    var tp = top(pc), tt = top(tc);
    var span = L.length ? dayNum(last) - dayNum(first) + 1 : 0;
    var T = [
      ['会话', String(L.length), ACT.map(function (k) { return SRC[k][1] + ' ' + (ns[k] || 0); }).join(' · ')],
      ['提问', String(nq), L.length ? '平均每个会话 ' + (nq / L.length).toFixed(1) + ' 次' : '—'],
      ['时间跨度', span ? span + ' 天' : '—', span ? first.slice(0, 10) + ' 起 · 有活动 ' + Object.keys(days).length + ' 天' : '—'],
      ['最活跃项目', tp ? null : '—', tp ? pc[tp] + ' 个会话 · ' + SRC[PSRC][1] : '当前筛选里没有 ' + SRC[PSRC][1] + ' 会话', tp, 1],
      ['最活跃主题', tt || '—', tt ? tc[tt] + ' 个会话' : '还没有主题标签', tt, 1]
    ];
    var box = $('tiles');
    box.textContent = '';
    T.forEach(function (t) {
      var c = el('div', 'tile');
      c.appendChild(el('div', 'tl-k', t[0]));
      var v = el('div', 'tl-v' + (t[4] ? ' txt' : ''), t[1]);
      if (t[1] === null) projInto(v, t[3]);
      if (t[3]) v.title = t[3];
      c.appendChild(v);
      c.appendChild(el('div', 'tl-s', t[2]));
      box.appendChild(c);
    });
  }

  // ---------- 按月堆叠柱 ----------
  var MONTHS = (function () {
    var a = D.map(function (d) { return d.start.slice(0, 7); }).filter(Boolean).sort(), out = [];
    if (!a.length) return out;
    var y = +a[0].slice(0, 4), m = +a[0].slice(5, 7), end = a[a.length - 1];
    for (;;) {
      var k = y + '-' + (m < 10 ? '0' : '') + m;
      out.push(k);
      if (k >= end || out.length > 240) break;
      if (++m > 12) { m = 1; y++; }
    }
    return out;
  })();
  function monthLabel(k) { return k.slice(0, 4) + ' 年 ' + (+k.slice(5, 7)) + ' 月'; }
  function niceStep(max) {
    var raw = max / 3, mag = Math.pow(10, Math.floor(Math.log10(raw || 1))), n = raw / mag;
    return Math.max(1, (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * mag);
  }
  function colPath(x, y, w, h, r) {
    r = Math.min(r, h, w / 2);
    return 'M' + x + ',' + (y + h) + 'V' + (y + r) + 'Q' + x + ',' + y + ' ' + (x + r) + ',' + y +
      'H' + (x + w - r) + 'Q' + (x + w) + ',' + y + ' ' + (x + w) + ',' + (y + r) + 'V' + (y + h) + 'Z';
  }
  var monthRows = [];
  var METRIC = { n: ['会话数', '个会话'], nq: ['提问数', '次提问'] };
  function renderMonths(L) {
    var c = {}, mt = METRIC[st.metric];
    MONTHS.forEach(function (k) { c[k] = { cc: 0, ai: 0, gpt: 0 }; });
    L.forEach(function (d) { var x = c[d.start.slice(0, 7)]; if (x) x[d.src] += st.metric === 'nq' ? d.nq || 0 : 1; });
    monthRows = MONTHS.map(function (k) { return { k: k, v: c[k], t: c[k].cc + c[k].ai + c[k].gpt }; });
    var max = 1;
    monthRows.forEach(function (r) { max = Math.max(max, r.t); });
    var step = niceStep(max), top = Math.ceil(max / step) * step;
    var W = 386, padL = 30, padR = 4, padT = 8, plotH = 116, base = padT + plotH, H = base + 34;
    var band = (W - padL - padR) / Math.max(1, MONTHS.length), bw = Math.min(24, band * 0.64);
    $('m-title').textContent = '每月' + mt[0];
    [].forEach.call($('metric').children, function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-m') === st.metric)); });
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'viz', role: 'img', 'aria-label': '每月' + mt[0] + '，' + ACT.map(function (k) { return SRC[k][0]; }).join(' 与 ') + (ACT.length > 1 ? ' 堆叠' : '') });
    for (var v = 0; v <= top; v += step) {
      var y = base - v / top * plotH;
      s.appendChild(svg('line', { x1: padL, x2: W - padR, y1: y, y2: y, class: v ? 'grid' : 'axis' }));
      s.appendChild(svg('text', { x: padL - 6, y: y + 3.5, class: 'tick', 'text-anchor': 'end' }, String(v)));
    }
    monthRows.forEach(function (r, i) {
      var x = padL + i * band + (band - bw) / 2, dim = st.month && st.month !== r.k ? ' dim' : '', used = 0;
      var segs = ACT.filter(function (k) { return r.v[k] > 0; });   // 自下而上堆叠，段间留 2px 底色缝，最上面一段圆角
      segs.forEach(function (k, j) {
        var hs = r.v[k] / top * plotH, gap = used > 0 ? 2 : 0, h = Math.max(1, hs - gap);
        s.appendChild(svg('path', { d: colPath(x, base - used - gap - h, bw, h, j === segs.length - 1 ? 4 : 0), class: 'm-' + k + dim }));
        used += hs;
      });
      var cx = padL + i * band + band / 2, mo = +r.k.slice(5, 7);
      s.appendChild(svg('text', { x: cx, y: base + 14, class: 'tick' + (st.month === r.k ? ' on' : ''), 'text-anchor': 'middle' }, mo + '月'));
      if (i === 0 || mo === 1) s.appendChild(svg('text', { x: cx, y: base + 28, class: 'tick yr', 'text-anchor': 'middle' }, r.k.slice(0, 4)));
      var hit = svg('rect', { x: padL + i * band, y: padT, width: band, height: plotH, class: 'hit', 'data-i': i, tabindex: 0, 'aria-label': monthLabel(r.k) + '：' + ACT.map(function (k) { return SRC[k][1] + ' ' + r.v[k]; }).join('，') + ' ' + mt[1] });
      s.appendChild(hit);
    });
    var box = $('months');
    box.textContent = '';
    box.appendChild(s);

    var t = el('table'), hr = el('tr');
    t.appendChild(el('caption', null, mt[0]));
    ['月份'].concat(ACT.map(function (k) { return SRC[k][0]; }), ACT.length > 1 ? ['合计'] : []).forEach(function (h) { hr.appendChild(el('th', null, h)); });
    t.appendChild(hr);
    monthRows.slice().reverse().forEach(function (r) {
      var tr = el('tr');
      [monthLabel(r.k)].concat(ACT.map(function (k) { return r.v[k]; }), ACT.length > 1 ? [r.t] : []).forEach(function (x) { tr.appendChild(el('td', null, String(x))); });
      t.appendChild(tr);
    });
    $('months-table').textContent = '';
    $('months-table').appendChild(t);
  }
  function monthTip(i, ev) {
    var r = monthRows[i];
    if (!r) return;
    showTip(ev, monthLabel(r.k), [[String(r.t), METRIC[st.metric][1]]].concat(ACT.map(function (k) { return [String(r.v[k]), SRC[k][0], k]; })), monthFoot(r.k));
  }
  function monthFoot(k) { return st.month === k ? '再点一次取消月份筛选' : '点击只看这个月'; }

  // ---------- 按天热力格 ----------
  var DAY0 = Infinity, DAY1 = -Infinity;
  D.forEach(function (d) {
    if (d.start) DAY0 = Math.min(DAY0, dayNum(d.start));
    if (d._last) DAY1 = Math.max(DAY1, dayNum(d._last));
  });
  var BASE = isFinite(DAY0) ? DAY0 - (new Date(DAY0 * 864e5).getUTCDay() + 6) % 7 : 0;
  if (isFinite(DAY1) && DAY1 - BASE < 53 * 7) BASE -= Math.ceil((53 * 7 - (DAY1 - BASE)) / 7) * 7;   // 数据不满一年也按一年宽画，免得格子被拉大
  var heatDays = {};
  function iso(n) { return new Date(n * 864e5).toISOString().slice(0, 10); }
  function renderHeat(L) {
    var box = $('heat');
    box.textContent = '';
    if (!isFinite(DAY0)) return;
    heatDays = {};
    L.forEach(function (d) {
      var n = dayNum(d.start), x = heatDays[n] || (heatDays[n] = { cc: 0, ai: 0, gpt: 0 });
      x[d.src]++;
    });
    // 固定档位（不随筛选变）：0 · 1–2 · 3–5 · 6–9 · 10+
    function lvl(n) { return !n ? 0 : n <= 2 ? 1 : n <= 5 ? 2 : n <= 9 ? 3 : 4; }

    var P = 12, C = 10, left = 20, topY = 26;
    var weeks = Math.floor((DAY1 - BASE) / 7) + 1, W = left + weeks * P, H = topY + 7 * P;
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'viz heatmap', role: 'img', 'aria-label': '每天会话数热力格，每列是一周' });
    [0, 2, 4].forEach(function (r) {
      s.appendChild(svg('text', { x: 0, y: topY + r * P + 8.5, class: 'tick' }, WEEK[r]));
    });
    var lastMonth = '';
    for (var w = 0; w < weeks; w++) {
      var mon = iso(BASE + w * 7), mk = mon.slice(0, 7);
      if (mk !== lastMonth) {
        var x = left + w * P;
        s.appendChild(svg('text', { x: x, y: 21, class: 'tick' }, (+mk.slice(5, 7)) + '月'));
        if (!lastMonth || mk.slice(5, 7) === '01') s.appendChild(svg('text', { x: x, y: 9, class: 'tick yr' }, mk.slice(0, 4)));
        lastMonth = mk;
      }
      for (var r = 0; r < 7; r++) {
        var n = BASE + w * 7 + r;
        if (n < DAY0 || n > DAY1) continue;
        var c = heatDays[n], tot = c ? c.cc + c.ai + c.gpt : 0;
        var dim = st.month && iso(n).slice(0, 7) !== st.month ? ' dim' : '';
        s.appendChild(svg('rect', { x: left + w * P, y: topY + r * P, width: C, height: C, rx: 2, class: 'hc l' + lvl(tot) + dim, 'data-n': n }));
      }
    }
    box.appendChild(s);
    box.scrollLeft = box.scrollWidth;  // 窄屏时先露出最近几个月

    var lg = $('heat-legend');
    lg.textContent = '';
    ['0', '1–2', '3–5', '6–9', '10+'].forEach(function (t, i) {
      var k = el('span', 'hk');
      k.appendChild(el('i', 'hsw l' + i));
      k.appendChild(document.createTextNode(t));
      lg.appendChild(k);
    });
  }
  function heatTip(n, ev) {
    var c = heatDays[n] || { cc: 0, ai: 0, gpt: 0 }, day = iso(n), tot = c.cc + c.ai + c.gpt;
    showTip(ev, day + ' 周' + WEEK[(new Date(n * 864e5).getUTCDay() + 6) % 7],
      [[String(tot), '个会话']].concat(ACT.map(function (k) { return [String(c[k]), SRC[k][0], k]; })),
      tot ? monthFoot(day.slice(0, 7)) : null);
  }

  // ---------- 悬停提示 ----------
  var tip = $('tip');
  function showTip(ev, title, rows, foot) {
    tip.textContent = '';
    tip.appendChild(el('div', 'tip-h', title));
    rows.forEach(function (r) {
      var d = el('div', 'tip-r');
      d.appendChild(el('i', 'key' + (r[2] ? ' ' + r[2] : ' none')));
      d.appendChild(el('b', null, r[0]));
      d.appendChild(el('span', null, r[1]));
      tip.appendChild(d);
    });
    if (foot) tip.appendChild(el('div', 'tip-f', foot));
    tip.hidden = false;
    var x, y;
    if (ev.clientX != null && ev.type !== 'focusin') { x = ev.clientX; y = ev.clientY; }
    else { var b = ev.target.getBoundingClientRect(); x = b.left + b.width / 2; y = b.top; }
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var left = x + 14 + tw > innerWidth - 8 ? x - tw - 14 : x + 14;
    var topY = y + 14 + th > innerHeight - 8 ? y - th - 14 : y + 14;
    tip.style.left = Math.max(8, left) + 'px';
    tip.style.top = Math.max(8, topY) + 'px';
  }
  function hideTip() { tip.hidden = true; }
  function bindChart(box, attr, fn, click) {
    function on(ev) {
      var t = ev.target.closest ? ev.target.closest('[' + attr + ']') : null;
      if (!t) { hideTip(); return; }
      fn(+t.getAttribute(attr), ev);
    }
    box.addEventListener('pointermove', on);
    box.addEventListener('focusin', on);
    box.addEventListener('pointerleave', hideTip);
    box.addEventListener('focusout', hideTip);
    box.addEventListener('click', function (ev) {
      var t = ev.target.closest ? ev.target.closest('[' + attr + ']') : null;
      if (t) click(+t.getAttribute(attr));
    });
    box.addEventListener('keydown', function (ev) {
      var t = ev.target.closest ? ev.target.closest('[' + attr + ']') : null;
      if (t && (ev.key === 'Enter' || ev.key === ' ')) {
        ev.preventDefault();
        var v = t.getAttribute(attr);
        click(+v);
        var f = box.querySelector('[' + attr + '="' + v + '"]');  // 图重画了，焦点放回同一根柱子
        if (f) f.focus();
      }
    });
  }
  function pickMonth(k) {  // 点柱子/格子：只看这个月；再点一次取消
    hideTip();
    st.month = st.month === k ? null : k;
    render();
  }
  bindChart($('months'), 'data-i', monthTip, function (i) { if (monthRows[i]) pickMonth(monthRows[i].k); });
  bindChart($('heat'), 'data-n', heatTip, function (n) { pickMonth(iso(n).slice(0, 7)); });

  // ---------- 分组列表 ----------
  function byRecent(a, b) { return a._last < b._last ? 1 : a._last > b._last ? -1 : 0; }
  var SORT = {
    recent: byRecent,
    nq: function (a, b) { return (b.nq - a.nq) || byRecent(a, b); },
    nmsg: function (a, b) { return (b.nmsg - a.nmsg) || byRecent(a, b); }
  };
  function groupsOf(L) {
    var map = {}, out = [];
    function add(k, d) {
      var g = map[k];
      if (!g) { g = map[k] = { key: k, items: [], nq: 0, nmsg: 0, c: {}, first: d.start, last: '' }; out.push(g); }
      g.items.push(d); g.nq += d.nq || 0; g.nmsg += d.nmsg || 0;
      g.c[d.src] = (g.c[d.src] || 0) + 1;
      if (d.start < g.first) g.first = d.start;
      if (d._last > g.last) g.last = d._last;
    }
    L.forEach(function (d) {
      if (st.group === 'proj') add(d._pk, d);
      else if (st.group === 'topic') (d._tp || [NOTOPIC]).forEach(function (t) { add(t, d); });
      else add(d.start.slice(0, 7), d);
    });
    out.forEach(function (g) { g.items.sort(SORT[st.sort]); });
    if (st.group === 'month') out.sort(function (a, b) { return a.key < b.key ? 1 : -1; });
    else out.sort(function (a, b) {
      if (a.key === NOTOPIC) return 1;
      if (b.key === NOTOPIC) return -1;
      return st.sort === 'recent' ? (a.last < b.last ? 1 : -1) : (b[st.sort] - a[st.sort]);
    });
    return out;
  }
  function groupTitle(k) {
    if (st.group === 'proj') return projInto(el('span', 'gn'), k);
    return el('span', 'gn', st.group === 'topic' ? (k === NOTOPIC ? '未分类' : k) : monthLabel(k));
  }
  function dateRange(a, b) { a = a.slice(0, 10); b = b.slice(0, 10); return a === b ? a : a + ' → ' + b; }
  function row(d, gk) {
    var a = el('a', 'row ' + d.src + (d.arch ? ' arch' : ''));
    a.href = d.href;
    a.appendChild(el('i', 'sw ' + d.src));
    var m = el('span', 'rm'), tl = el('span', 'tl'), tt = el('span', 'tt');
    if (d.star) tt.appendChild(el('span', 'star', '★'));
    tt.appendChild(document.createTextNode(d.t || '(无标题)'));
    tl.appendChild(tt);
    if (d.arch) tl.appendChild(el('span', 'badge', '已归档'));
    (d._tp || []).forEach(function (t) { if (t !== gk && t !== st.topic) tl.appendChild(el('span', 'tag', t)); });  // 分组/筛选已表明的主题不再重复
    m.appendChild(tl);
    if (d._sum) m.appendChild(el('span', 'sm' + (d.sum ? '' : ' fallback'), d._sum));
    a.appendChild(m);
    var wh = d.src === 'ai' ? el('span', 'where', 'claude.ai') : projInto(el('span', 'where'), d._pk);
    if (d.src !== 'ai') wh.title = d._pk;
    a.appendChild(wh);
    a.appendChild(el('span', 'nq', (d.nq || 0) + ' 问'));
    var w = el('span', 'when', when(d._last));
    w.title = d.start + ' ~ ' + d._last;
    a.appendChild(w);
    return a;
  }
  function renderList(L) {
    var box = $('list');
    box.textContent = '';
    box.className = 'list g-' + st.group;
    var G = groupsOf(L);
    if (!G.length) {
      box.appendChild(el('p', 'empty', '没有符合条件的会话。换个关键词，或点列表上方的“清除全部”。'));
      return;
    }
    G.forEach(function (g) {
      var ck = st.group + ':' + g.key, closed = !!collapsed[ck];
      var sec = el('section', 'grp' + (closed ? ' closed' : ''));
      var h = el('button', 'gh');
      h.type = 'button';
      h.setAttribute('aria-expanded', String(!closed));
      h.appendChild(el('span', 'chev'));
      h.appendChild(groupTitle(g.key));
      if (st.group === 'proj' && PSRC === 'cc' && g.key !== CHAT) h.appendChild(el('span', 'gp', g.key));
      var meta = el('span', 'gm'), bar = el('span', 'gbar');
      bar.title = ACT.map(function (k) { return SRC[k][1] + ' ' + (g.c[k] || 0); }).join(' · ');
      ACT.forEach(function (k) { if (g.c[k]) { var i = el('i', k); i.style.flexGrow = g.c[k]; bar.appendChild(i); } });
      meta.appendChild(bar);
      meta.appendChild(el('span', 'gs', g.items.length + ' 个会话 · ' + g.nq + ' 次提问'));
      meta.appendChild(el('span', 'gr', dateRange(g.first, g.last)));
      h.appendChild(meta);
      h.addEventListener('click', function () {
        if (collapsed[ck]) delete collapsed[ck]; else collapsed[ck] = 1;
        store('collapsed', JSON.stringify(collapsed));
        var c = !!collapsed[ck];
        sec.classList.toggle('closed', c);
        h.setAttribute('aria-expanded', String(!c));
        syncFold();
      });
      sec.appendChild(h);
      var rows = el('div', 'rows');
      var n = expanded[ck] ? g.items.length : Math.min(LIMIT, g.items.length);
      var gk = st.group === 'topic' ? g.key : null;
      for (var i = 0; i < n; i++) rows.appendChild(row(g.items[i], gk));
      if (n < g.items.length) {
        var more = el('button', 'more', '再显示 ' + (g.items.length - n) + ' 个');
        more.type = 'button';
        more.addEventListener('click', function () {
          expanded[ck] = 1;
          for (var j = n; j < g.items.length; j++) rows.insertBefore(row(g.items[j], gk), more);
          more.remove();
        });
        rows.appendChild(more);
      }
      sec.appendChild(rows);
      box.appendChild(sec);
    });
  }
  function syncFold() {
    var any = document.querySelector('#list .grp:not(.closed)');
    $('fold').textContent = any ? '全部折叠' : '全部展开';
  }
  $('fold').addEventListener('click', function () {
    var open = !!document.querySelector('#list .grp:not(.closed)');
    groupsOf(D.filter(function (d) { return ok(d); })).forEach(function (g) {
      var ck = st.group + ':' + g.key;
      if (open) collapsed[ck] = 1; else delete collapsed[ck];
    });
    store('collapsed', JSON.stringify(collapsed));
    render();
  });

  // ---------- 全文搜索（按需加载 search.js，file:// 下只能用 <script>） ----------
  var ft = $('ft'), loading = false, HREF = {};
  D.forEach(function (d) { HREF[d.href] = d; });
  function ftShow(title, note) {
    ft.textContent = '';
    var h = el('div', 'ft-head');
    h.appendChild(el('h2', null, title));
    var back = el('button', 'ghost', '返回列表');
    back.type = 'button';
    back.addEventListener('click', ftHide);
    h.appendChild(back);
    ft.appendChild(h);
    if (note) ft.appendChild(el('p', 'ft-note', note));
    ft.hidden = false;
    $('list').hidden = true;
  }
  function ftHide() { ft.hidden = true; $('list').hidden = false; }
  function fullText() {
    var raw = $('q').value.trim(), q = raw.toLowerCase();
    if (!q) return;
    if (!window.S || !window.P) {
      if (loading) return;
      loading = true;
      ftShow('全文搜索「' + raw + '」', '正在加载全文索引（约 21 MB，第一次要几秒）…');
      var sc = document.createElement('script');
      sc.src = 'search.js';
      sc.onload = function () {
        loading = false;
        (window.S || []).forEach(function (e) { e[3] = String(e[2]).toLowerCase(); });
        fullText();
      };
      sc.onerror = function () { loading = false; ftShow('全文搜索不可用', '没加载到 search.js。标题过滤不受影响。'); };
      document.body.appendChild(sc);
      return;
    }
    var S = window.S, P = window.P, pages = {}, order = [], nhit = 0;
    var extra = st.proj || st.topic || st.month || st.star;
    for (var i = 0; i < S.length; i++) {
      var e = S[i], k = e[3].indexOf(q);
      if (k < 0) continue;
      var p = P[e[0]];
      if (!p) continue;
      var d = HREF[p[0]] || HREF[p[0].replace(/\/agent-[^\/]+\.html$/, '.html')];
      if (d ? !ok(d, 'q') : (extra || (st.src !== 'all' && p[2] !== st.src))) continue;
      nhit++;
      var g = pages[e[0]];
      if (!g) { g = pages[e[0]] = { p: p, d: d, n: 0, hits: [], seen: {} }; order.push(g); }
      g.n++;
      var sig = e[3].slice(Math.max(0, k - 30), k + 60);  // 分支重发的同一段话只显示一次
      if (g.hits.length < 3 && !g.seen[sig]) { g.seen[sig] = 1; g.hits.push([e, k]); }
    }
    order.sort(function (a, b) { return b.n - a.n; });
    var shown = order.slice(0, 80);
    ftShow('全文搜索「' + raw + '」',
      nhit ? '在 ' + order.length + ' 个页面里命中 ' + nhit + ' 条消息' + (order.length > 80 ? '，按命中多少只列前 80 个' : '') + '，每个页面最多显示 3 段。'
           : '没有命中。试试更短的词，或者检查左侧筛选。');
    shown.forEach(function (g) {
      var sec = el('section', 'ft-page');
      var hd = el('div', 'ft-ph');
      hd.appendChild(el('i', 'sw ' + g.p[2]));
      var a = el('a', null, g.p[1] || '(无标题)');
      a.href = g.p[0];
      hd.appendChild(a);
      var sub = /\/agent-/.test(g.p[0]);
      if (sub) hd.appendChild(el('span', 'badge', '子 agent'));
      hd.appendChild(el('span', 'ft-n', g.n + ' 处'));
      sec.appendChild(hd);
      if (g.d) {  // 第二行：属于哪个会话（子 agent 页给出主会话）· 来源/项目 · 日期
        var mt = el('div', 'ft-meta');
        if (sub) {
          mt.appendChild(document.createTextNode('属于会话 '));
          var pa = el('a', null, g.d.t || '(无标题)');
          pa.href = g.d.href;
          mt.appendChild(pa);
          mt.appendChild(document.createTextNode(' · '));
        }
        if (g.d.src === 'ai') mt.appendChild(document.createTextNode('claude.ai'));
        else projInto(mt, g.d._pk);
        mt.appendChild(document.createTextNode(' · ' + when(g.d.start)));
        sec.appendChild(mt);
      }
      g.hits.forEach(function (h) {
        var e = h[0], k = h[1], t = String(e[2]), s = el('a', 'snip');
        s.href = g.p[0] + '#' + e[1];
        var from = Math.max(0, k - 50), to = Math.min(t.length, k + q.length + 80);
        function flat(x) { return x.replace(/\s+/g, ' '); }
        s.appendChild(document.createTextNode((from ? '…' : '') + flat(t.slice(from, k))));
        s.appendChild(el('mark', null, t.slice(k, k + q.length)));
        s.appendChild(document.createTextNode(flat(t.slice(k + q.length, to)) + (to < t.length ? '…' : '')));
        sec.appendChild(s);
      });
      ft.appendChild(sec);
    });
  }

  // ---------- 当前筛选条件（列表上方的小标签） ----------
  function clearQ() { qi.value = ''; st.q = ''; ftHide(); }
  function renderChips() {
    var C = [], box = $('chips');
    if (st.src !== 'all') C.push(['来源', SRC[st.src][0], function () { st.src = 'all'; }, st.src]);
    if (st.proj) C.push(['项目', null, function () { st.proj = null; }]);
    if (st.topic) C.push(['主题', st.topic === NOTOPIC ? '未分类' : st.topic, function () { st.topic = null; }]);
    if (st.month) C.push(['月份', st.month, function () { st.month = null; }]);
    if (st.star) C.push(['标记', '只看星标', function () { st.star = false; }]);
    if (st.q) C.push(['搜索', '“' + qi.value.trim() + '”', clearQ]);
    box.textContent = '';
    box.hidden = !C.length;
    C.forEach(function (c) {
      var b = el('button', 'chip');
      b.type = 'button';
      b.appendChild(el('span', 'ck', c[0]));
      if (c[3]) b.appendChild(el('i', 'sw ' + c[3]));
      if (c[1] === null) projInto(b, st.proj); else b.appendChild(document.createTextNode(c[1]));
      b.appendChild(el('span', 'cx', '×'));
      b.setAttribute('aria-label', '去掉筛选：' + c[0] + ' ' + (c[1] === null ? projName(st.proj) : c[1]));
      b.addEventListener('click', function () { c[2](); render(); });
      box.appendChild(b);
    });
    if (C.length) {
      var all = el('button', 'chip clear', '清除全部');
      all.type = 'button';
      all.addEventListener('click', function () {
        st.src = 'all'; st.proj = st.topic = st.month = null; st.star = false; clearQ(); render();
      });
      box.appendChild(all);
    }
  }

  // ---------- 总渲染与控件 ----------
  function render() {
    var L = D.filter(function (d) { return ok(d); });
    var M = D.filter(function (d) { return ok(d, 'month'); });  // 图表不按月份筛，选中的月份高亮
    renderSide();
    renderTiles(L);
    renderMonths(M);
    renderHeat(M);
    renderList(L);
    renderChips();
    $('count').textContent = L.length === D.length ? '共 ' + D.length + ' 个会话' : '显示 ' + L.length + ' / ' + D.length;
    [].forEach.call($('group').children, function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-g') === st.group)); });
    $('sort').value = st.sort;
    syncFold();
  }

  var qi = $('q'), timer = 0;
  qi.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { st.q = qi.value.trim().toLowerCase(); ftHide(); render(); }, 80);
  });
  qi.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') { ev.preventDefault(); fullText(); }
    if (ev.key === 'Escape') { clearQ(); render(); }
  });
  document.addEventListener('keydown', function (ev) {
    var t = ev.target && ev.target.tagName;
    if (ev.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(t || '') && !ev.ctrlKey && !ev.metaKey) { ev.preventDefault(); qi.focus(); }
  });
  $('group').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-g]');
    if (!b) return;
    st.group = b.getAttribute('data-g');
    store('group', st.group);
    render();
  });
  $('sort').addEventListener('change', function () { st.sort = this.value; store('sort', st.sort); render(); });
  $('metric').addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-m]');
    if (!b) return;
    st.metric = b.getAttribute('data-m');
    store('metric', st.metric);
    render();
  });

  // 分享/截图用 URL 参数（不写进记忆）：?group= &metric= &src= &proj= &topic= &month= &star=1 &fts=关键词（打开即全文搜索）
  var U = new URLSearchParams(location.search), fts = U.get('fts');
  if (/^(proj|topic|month)$/.test(U.get('group'))) st.group = U.get('group');
  if (/^(n|nq)$/.test(U.get('metric'))) st.metric = U.get('metric');
  if (/^(cc|ai|gpt)$/.test(U.get('src'))) st.src = U.get('src');
  ['proj', 'topic', 'month'].forEach(function (k) { if (U.get(k)) st[k] = U.get(k); });
  if (U.get('star')) st.star = true;
  if (fts) { qi.value = fts; st.q = fts.trim().toLowerCase(); }
  ACT.forEach(function (k) { var lg = $('src-legend'); lg.appendChild(el('i', 'sw ' + k)); lg.appendChild(document.createTextNode(SRC[k][0])); });
  render();
  if (fts) fullText();
})();
