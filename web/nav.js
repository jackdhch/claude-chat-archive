(function(){var qs=[].slice.call(document.querySelectorAll('.m.u,.m.p')).filter(function(q){return !q.closest('details')});if(!qs.length)return;
var rail=document.createElement('nav');rail.id='rail';var list=document.createElement('div');list.id='qlist';rail.appendChild(list);
function mk(q,i,cls){var a=document.createElement('a');a.href='#'+q.id;a.className=cls;if(cls==='it')a.textContent=(i+1)+'. '+(q.dataset.s||'');
 a.onclick=function(e){e.preventDefault();q.scrollIntoView({block:'start'});history.replaceState(null,'','#'+q.id)};return a}
var ticks=qs.map(function(q,i){var t=mk(q,i,'tk');t.style.top=(qs.length>1?i/(qs.length-1)*100:0)+'%';rail.appendChild(t);return t});
var items=qs.map(function(q,i){var a=mk(q,i,'it');list.appendChild(a);return a});
var bar=document.createElement('div');bar.id='qnav';var up=document.createElement('button'),dn=document.createElement('button'),pos=document.createElement('span');
up.textContent='▲';up.title=window.LANG==='zh'?'上一个提问（k）':'Previous prompt (k)';dn.textContent='▼';dn.title=window.LANG==='zh'?'下一个提问（j）':'Next prompt (j)';bar.appendChild(up);bar.appendChild(pos);bar.appendChild(dn);
document.body.appendChild(rail);document.body.appendChild(bar);
function top(q){return q.getBoundingClientRect().top}
function cur(){var c=-1;for(var i=0;i<qs.length;i++){if(top(qs[i])<=40)c=i;else break}return c}
var last=-2;function upd(){var c=cur();if(c===last)return;last=c;ticks.forEach(function(t,i){t.classList.toggle('on',i===c)});items.forEach(function(t,i){t.classList.toggle('on',i===c)});pos.textContent=Math.max(c+1,0)+'/'+qs.length}
rail.addEventListener('mouseenter',function(){var a=items[Math.max(last,0)];list.scrollTop=a.offsetTop-list.clientHeight/2});
function go(d){var i;if(d>0){for(i=0;i<qs.length&&top(qs[i])<=20;i++);}else{for(i=qs.length-1;i>=0&&top(qs[i])>=0;i--);}
 if(i>=0&&i<qs.length){qs[i].scrollIntoView({block:'start'});history.replaceState(null,'','#'+qs[i].id)}}
up.onclick=function(){go(-1)};dn.onclick=function(){go(1)};
document.addEventListener('keydown',function(e){if(/INPUT|TEXTAREA/.test((e.target||{}).tagName||'')||e.ctrlKey||e.metaKey||e.altKey)return;if(e.key==='j')go(1);if(e.key==='k')go(-1)});
var t=0;addEventListener('scroll',function(){if(!t)t=requestAnimationFrame(function(){t=0;upd()})});upd()})();