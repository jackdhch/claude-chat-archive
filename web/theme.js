// 主题：URL 参数 ?theme=dark|light 最优先（截图用，不记住）；其次是上次点按钮的选择；都没有就跟随系统。
// 放在 <head> 里同步执行，避免先闪一下错的颜色。按钮放进 #theme-slot，没有这个元素就挂在页面右上角。
(function () {
  var root = document.documentElement, key = 'theme';
  var m = /[?&]theme=(dark|light)\b/.exec(location.search), t = m && m[1];
  if (!t) { try { t = localStorage.getItem(key); } catch (e) {} }
  if (t === 'dark' || t === 'light') root.setAttribute('data-theme', t);

  function cur() {
    return root.getAttribute('data-theme') ||
      (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }
  document.addEventListener('DOMContentLoaded', function () {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'theme-btn';
    function label() {
      var next = cur() === 'dark' ? '浅色' : '深色';
      b.textContent = '切换' + next;
      b.setAttribute('aria-label', '切换到' + next + '模式');
    }
    b.addEventListener('click', function () {
      var n = cur() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', n);
      try { localStorage.setItem(key, n); } catch (e) {}
      label();
    });
    label();
    (document.getElementById('theme-slot') || document.body).appendChild(b);
  });
})();
