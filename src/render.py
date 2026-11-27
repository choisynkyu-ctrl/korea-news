"""날짜별 JSON으로 대시보드 HTML을 만든다 (시세 타일 · 관심 종목 · 뉴스 TOP 10)."""
import json
from collections import Counter
from datetime import date
from html import escape

from .config import ARCHIVE_DIR, CATEGORIES, DATA_DIR, DOCS, HOLDINGS_GROUP

WEEKDAYS = "월화수목금토일"

CAT_COLORS = {
    "정치": "#3b6fd9",
    "경제/정책": "#1f9d6b",
    "증시/금융": "#c2410c",
    "산업/기업": "#7a4fd6",
    "부동산": "#a16207",
    "사회": "#b8478f",
    "IT/과학": "#2f9bb0",
    "국제/외교": "#4f6b8a",
    "기타": "#6b7280",
}

# 국내 관례: 상승 빨강 · 하락 파랑 (항상 ▲▼ 기호와 함께 표시해 색만으로 구분하지 않음)
CSS = """
:root{--bg:#f5f6f8;--card:#fff;--text:#16181d;--muted:#606773;--line:#e3e6eb;--accent:#16181d;--chip:#eef0f3;--up:#d42b36;--down:#1d5fd1;--flat:#6b7280;--up-fill:rgba(212,43,54,.08);--down-fill:rgba(29,95,209,.08)}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--text:#eceef2;--muted:#9aa1ad;--line:#2a2e36;--accent:#eceef2;--chip:#22262e;--up:#ff6b72;--down:#6aa5ff;--flat:#9aa1ad;--up-fill:rgba(255,107,114,.10);--down-fill:rgba(106,165,255,.10)}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Pretendard,-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:32px 16px 64px}
header{margin-bottom:8px}
.eyebrow{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-size:30px;line-height:1.25;margin:6px 0 10px;letter-spacing:-.02em}
.digest{margin:16px 0 0;display:grid;gap:10px;max-width:860px}
.digest .row{display:grid;grid-template-columns:64px 1fr;gap:12px;align-items:baseline}
.digest .lbl{font-size:12px;font-weight:700;text-align:center;background:var(--chip);border-radius:6px;padding:3px 0}
.digest p{margin:0;font-size:15px}
.digest .lines{display:grid;gap:4px}
.digest .kind{display:inline-block;font-size:11px;font-weight:700;color:var(--muted);border:1px solid var(--line);border-radius:5px;padding:0 6px;margin-right:8px;vertical-align:2px}
.digest .row:first-child p{font-size:16px;font-weight:600}
.digest .span{font-size:12px;color:var(--muted);margin-left:6px;white-space:nowrap}
.digest.news{margin:0 0 16px}
nav.days{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
nav.days a{font-size:13px;color:var(--muted);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:4px 12px}
nav.days a:hover{color:var(--text);border-color:var(--muted)}
h2.sec{font-size:20px;margin:36px 0 12px;letter-spacing:-.01em;display:flex;align-items:baseline;gap:10px}
h2.sec small{font-size:12px;font-weight:500;color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media (max-width:860px){.tiles{grid-template-columns:repeat(3,minmax(0,1fr))}}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px 10px;display:flex;flex-direction:column;gap:2px;min-width:0}
.tile .grp{font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.02em}
.tile .nm{font-size:14px;font-weight:600}
.tile .px{font-size:24px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.3}
.chg{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--flat)}
.spark{position:relative;margin-top:6px;display:flex;flex-direction:column}
.spark svg{order:1}.qlabels{order:2}
.spark svg{display:block;width:100%;height:44px;overflow:visible}
.spark .tip{display:block;order:3;min-height:15px;margin-top:1px;font-size:11px;line-height:15px;color:var(--text);text-align:right;font-variant-numeric:tabular-nums}
.spark .guide{stroke:var(--muted);stroke-width:1;opacity:0}
.spark:hover .guide{opacity:.5}
.tile .foot span{white-space:nowrap}
.tile .foot{display:flex;justify-content:space-between;flex-wrap:wrap;gap:0 6px;font-size:12px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:4px}
.spark .qline{stroke:var(--muted);stroke-width:1;stroke-dasharray:2 3;opacity:.45}
.qlabels{position:relative;height:13px;margin-top:2px}
.qlabels span{position:absolute;top:0;font-size:10px;color:var(--muted);padding-left:3px;line-height:13px}
.comment{margin:0 0 12px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:grid;grid-template-columns:52px 1fr;gap:12px;align-items:baseline}
.comment .lbl{font-size:12px;font-weight:700;text-align:center;background:var(--chip);border-radius:6px;padding:3px 0}
.comment p{margin:0;font-size:15px}
.tablewrap{margin-top:12px;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
th,td{padding:10px 14px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
th{font-size:12px;font-weight:600;color:var(--muted);cursor:pointer;user-select:none}
th[aria-sort=descending]::after{content:" ↓"}th[aria-sort=ascending]::after{content:" ↑"}
th:first-child,td:first-child{text-align:left}
td .code{font-size:11px;color:var(--muted);margin-left:6px}
td .no{display:inline-block;min-width:20px;font-size:12px;font-weight:700;color:var(--muted)}
th:first-child,td:first-child{position:sticky;left:0;background:var(--card);z-index:1}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 4px}
.tabs button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:999px;padding:6px 14px;cursor:pointer}
.tabs button[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.empty{color:var(--muted);font-size:14px}
.mine{display:inline-block;margin-left:6px;font-size:11px;font-weight:700;color:var(--accent);border:1px solid var(--accent);border-radius:5px;padding:0 5px;vertical-align:1px}
tr.pin td{background:var(--chip)}
.group .note{margin:8px 2px 0;font-size:12px;color:var(--muted)}
td.sp{width:150px;padding-top:4px;padding-bottom:4px}
td.sp .spark{margin:0}td.sp .spark svg{height:28px}td.sp .tip{display:none!important}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px}
.filters button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:999px;padding:6px 14px;cursor:pointer}
.filters button[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.filters .n{opacity:.6;margin-left:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:10px}
.card.top{grid-column:1/-1}
.card.top h3{font-size:24px}
.meta{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);flex-wrap:wrap}
.rank{font-weight:800;font-size:15px;color:var(--text);min-width:22px}
.cat{font-weight:600;padding:2px 8px;border-radius:6px;color:#fff}
h3{font-size:18px;line-height:1.4;margin:0;letter-spacing:-.01em}
.summary{margin:0;font-size:15px}
.why{margin:0;font-size:14px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px}
.related{display:flex;gap:6px;flex-wrap:wrap;font-size:12px}
.related span{border:1px solid var(--line);border-radius:6px;padding:1px 8px}
.related span::before{content:"# ";color:var(--muted)}
.sources{display:flex;gap:6px;flex-wrap:wrap;margin-top:auto;padding-top:6px}
.sources a{font-size:12px;color:var(--muted);background:var(--chip);border-radius:6px;padding:3px 8px;text-decoration:none}
.sources a:hover{color:var(--text)}
/* 보유 수익 (비밀번호로 풀림) */
.pf{margin:12px 0 0}
.pf-lock{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.pf [hidden]{display:none!important}
.pf-lock .t{font-weight:700;font-size:15px}.pf-lock .t small{font-weight:500;color:var(--muted);font-size:12px;margin-left:6px}
.pf-lock .f{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-left:auto}
.pf-lock input[type=password]{font:inherit;font-size:14px;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text);width:150px}
.pf-lock label{font-size:12px;color:var(--muted);display:flex;gap:4px;align-items:center}
.pf button{font:inherit;font-size:13px;border:1px solid var(--accent);background:var(--accent);color:var(--bg);border-radius:999px;padding:6px 14px;cursor:pointer}
.pf button.ghost{background:transparent;color:var(--muted);border-color:var(--line);padding:3px 10px;font-size:12px}
.pf-lock .err{flex-basis:100%;font-size:12px;color:var(--up)}.pf-lock .err:empty{display:none}
.pf-sum{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:2px;min-width:0}
.kpi .k,.pf-item .k{font-size:12px;font-weight:600;color:var(--muted)}
.kpi .v{font-size:28px;font-weight:800;letter-spacing:-.02em;line-height:1.25;font-variant-numeric:tabular-nums;white-space:nowrap}
.kpi .s{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.kpi .s b{font-weight:600}
.pf-items{display:grid;gap:10px;margin-top:12px}
.pf-item{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.pf-item .hd{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px}
.pf-item .hd b{font-size:15px}.pf-item .hd .code{font-size:11px;color:var(--muted)}
.pf-item .hd .q{font-size:12px;color:var(--muted);margin-left:auto;font-variant-numeric:tabular-nums}
.pf-item .nums{display:grid;grid-template-columns:1.2fr .8fr 1.4fr;gap:10px;margin-top:8px}
.pf-item .nums>div{display:flex;flex-direction:column;min-width:0}
.pf-item .v{font-size:20px;font-weight:800;letter-spacing:-.01em;font-variant-numeric:tabular-nums;white-space:nowrap}
.pf-item .s{font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.pf-bar{position:relative;height:6px;border-radius:3px;background:var(--chip);margin-top:10px}
.pf-bar i{position:absolute;top:0;bottom:0;border-radius:3px}
.pf-bar::after{content:"";position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--muted);opacity:.5}
.pf-foot{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:8px;font-size:12px;color:var(--muted)}
@media (max-width:640px){.pf-sum{grid-template-columns:1fr;gap:8px}.kpi .v{font-size:24px}.pf-item .nums{grid-template-columns:1fr 1fr}.pf-item .nums>div:last-child{grid-column:1/-1}.pf-lock .f{margin-left:0}.pf-item .hd .q{margin-left:0;flex-basis:100%}}
footer{margin-top:40px;font-size:12px;color:var(--muted)}
@media (max-width:520px){h1{font-size:24px}.grid{grid-template-columns:1fr}.card.top h3{font-size:20px}
.digest .row,.comment{grid-template-columns:1fr;gap:4px}.digest .lbl,.comment .lbl{justify-self:start;padding:2px 8px}
.tiles{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.tile{padding:12px}.tile .px{font-size:19px}
td.sp{width:96px}th,td{padding:9px 10px}}
"""

JS = """
const btns=document.querySelectorAll('.filters button');
btns.forEach(b=>b.addEventListener('click',()=>{
  btns.forEach(x=>x.setAttribute('aria-pressed',x===b));
  const c=b.dataset.cat;
  document.querySelectorAll('.card').forEach(el=>{el.hidden=!(c==='all'||el.dataset.cat===c)});
}));
// 추이 그래프: 마우스/터치한 날짜·값 + 그 날짜가 속한 분기의 '분기 시작 대비 현재' 등락률
document.querySelectorAll('.spark').forEach(sp=>{
  const pts=JSON.parse(sp.dataset.p),qs=JSON.parse(sp.dataset.q||'[]'),dec=+sp.dataset.dec,tip=sp.querySelector('.tip'),g=sp.querySelector('.guide'),svg=sp.querySelector('svg');
  if(!tip||sp.closest('td'))return;
  const fmt=v=>v.toLocaleString('ko-KR',{minimumFractionDigits:dec,maximumFractionDigits:dec});
  const show=e=>{
    const r=svg.getBoundingClientRect(),i=Math.max(0,Math.min(pts.length-1,Math.round((e.clientX-r.left)/r.width*(pts.length-1))));
    const x=pts.length<2?0:i/(pts.length-1)*200;g.setAttribute('x1',x);g.setAttribute('x2',x);g.style.opacity=.5;
    const [d,v]=pts[i];let t=d.slice(5).replace('-','/')+' '+fmt(v);
    const q=qs.filter(q=>q[0]<=d).pop();
    if(q&&q[2]!==null)t+=' · '+q[1]+'→현재 '+(q[2]>0?'+':'')+q[2].toFixed(1)+'%';
    tip.textContent=t;
  };
  sp.addEventListener('pointermove',show);sp.addEventListener('pointerdown',show);
  sp.addEventListener('pointerleave',()=>{tip.textContent='';g.style.opacity=''});
});
// 업종 버튼
const tabs=document.querySelectorAll('.tabs button');
function showGroup(g){tabs.forEach(x=>x.setAttribute('aria-pressed',x.dataset.g===g));document.querySelectorAll('.group').forEach(p=>{p.hidden=p.dataset.g!==g});}
tabs.forEach(b=>b.addEventListener('click',()=>{showGroup(b.dataset.g);try{localStorage.setItem('kb-group',b.textContent)}catch(e){}}));
try{const saved=localStorage.getItem('kb-group');const t=[...tabs].find(x=>x.textContent===saved);if(t)showGroup(t.dataset.g)}catch(e){}
// 보유 수익: 암호문을 비밀번호로 풀어 이 브라우저 안에서만 그린다 (PBKDF2-SHA256 → AES-GCM)
document.querySelectorAll('.pf').forEach(pf=>{
  const enc=JSON.parse(pf.dataset.enc),form=pf.querySelector('form'),body=pf.querySelector('.pf-body'),err=pf.querySelector('.err'),KEY='kb-pf';
  const b64=t=>Uint8Array.from(atob(t),c=>c.charCodeAt(0));
  const won=v=>Math.round(v).toLocaleString('ko-KR')+'원';
  const sgn=v=>v>0?'up':v<0?'down':'flat',arr=v=>v>0?'▲ ':v<0?'▼ ':'';
  const pct=v=>(v>0?'+':'')+v.toFixed(2)+'%';
  const md=d=>+d.slice(5,7)+'/'+(+d.slice(8));
  const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const freq=n=>n>=10?'월 지급':n>=3?'분기 지급':n?'연 '+n+'회':'';
  async function open(pw){
    const k=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveKey']);
    const key=await crypto.subtle.deriveKey({name:'PBKDF2',salt:b64(enc.salt),iterations:enc.iter,hash:'SHA-256'},k,{name:'AES-GCM',length:256},false,['decrypt']);
    return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:b64(enc.iv)},key,b64(enc.ct))));
  }
  function draw(p){
    const t=p.total,mx=Math.max(...p.rows.map(r=>Math.abs(r.ret)),1);
    let h='<div class="pf-sum">'
      +'<div class="kpi"><span class="k">평가손익</span><span class="v '+sgn(t.pnl)+'">'+arr(t.pnl)+won(Math.abs(t.pnl))+'</span><span class="s">평가 <b>'+won(t.value)+'</b> · 매수 '+won(t.cost)+'</span></div>'
      +'<div class="kpi"><span class="k">수익률</span><span class="v '+sgn(t.ret)+'">'+pct(t.ret)+'</span><span class="s">오늘 <b class="'+sgn(t.day)+'">'+arr(t.day)+won(Math.abs(t.day))+' ('+pct(t.day_pct)+')</b></span></div>'
      +'<div class="kpi"><span class="k">배당금 (연간)</span><span class="v">'+won(t.div_year)+'</span><span class="s">세후 약 <b>'+won(t.div_after_tax)+'</b> · 월 평균 '+won(t.div_after_tax/12)+'</span></div>'
      +'</div><div class="pf-items">';
    p.rows.forEach(r=>{
      const w=Math.abs(r.ret)/mx*50,dl=r.div_last;
      h+='<div class="pf-item"><div class="hd"><b>'+esc(r.name)+'</b><span class="code">'+esc(r.code)+'</span><span class="q">'+r.qty.toLocaleString('ko-KR')+'주 · 평단 '+won(r.avg)+' → 현재 '+won(r.price)+'</span></div>'
        +'<div class="nums"><div><span class="k">평가손익</span><span class="v '+sgn(r.pnl)+'">'+arr(r.pnl)+won(Math.abs(r.pnl))+'</span><span class="s">평가 '+won(r.value)+'</span></div>'
        +'<div><span class="k">수익률</span><span class="v '+sgn(r.ret)+'">'+pct(r.ret)+'</span><span class="s">오늘 <span class="'+sgn(r.day)+'">'+pct(r.day_pct)+'</span></span></div>'
        +'<div><span class="k">배당금 (연간)</span><span class="v">'+(r.div_year?won(r.div_year):'없음')+'</span><span class="s">'
        +(dl?freq(r.div_count)+' · 최근 '+md(dl.date)+' 주당 '+won(dl.amount)+' → '+won(dl.total)+' · 매수가 대비 연 '+r.div_yoc.toFixed(1)+'%':'최근 1년 분배금 없음')+'</span></div></div>'
        +'<div class="pf-bar" role="img" aria-label="수익률 '+pct(r.ret)+'"><i style="background:var(--'+sgn(r.ret)+');'+(r.ret>=0?'left:50%':'right:50%')+';width:'+w.toFixed(1)+'%"></i></div></div>';
    });
    h+='</div><div class="pf-foot"><span>'+md(p.date)+' 종가 기준 · 배당금은 최근 12개월 분배금 × 보유 수량 (세전, 세후는 15.4% 제외)</span><button type="button" class="ghost">잠그기</button></div>';
    body.innerHTML=h;body.hidden=false;form.hidden=true;
    body.querySelector('.ghost').addEventListener('click',()=>{try{localStorage.removeItem(KEY)}catch(e){}body.hidden=true;body.innerHTML='';form.hidden=false;form.querySelector('input[type=password]').value=''});
  }
  form.addEventListener('submit',async e=>{
    e.preventDefault();const pw=form.querySelector('input[type=password]').value;err.textContent='';
    try{const p=await open(pw);draw(p);if(form.querySelector('input[type=checkbox]').checked)try{localStorage.setItem(KEY,pw)}catch(e){}}
    catch(x){err.textContent=window.crypto&&crypto.subtle?'비밀번호가 맞지 않습니다.':'이 브라우저에서는 열 수 없습니다 (https 주소로 열어 주세요).'}
  });
  let saved=null;try{saved=localStorage.getItem(KEY)}catch(e){}
  if(saved)open(saved).then(draw).catch(()=>{try{localStorage.removeItem(KEY)}catch(e){}});
});
// 종목 표 정렬
document.querySelectorAll('table.sortable').forEach(t=>{
  t.querySelectorAll('th[data-k]').forEach((th,ci)=>th.addEventListener('click',()=>{
    const k=th.dataset.k,cur=th.getAttribute('aria-sort'),desc=k==='rank'?cur==='ascending':cur!=='descending',tb=t.tBodies[0];
    t.querySelectorAll('th').forEach(x=>x.removeAttribute('aria-sort'));th.setAttribute('aria-sort',desc?'descending':'ascending');
    [...tb.rows].sort((a,b)=>{const x=a.dataset[k],y=b.dataset[k];const r=(x===''||y==='')?(x===''?-1:1):isNaN(x)?x.localeCompare(y,'ko'):x-y;return desc?-r:r}).forEach(r=>tb.appendChild(r));
  }));
});
"""


def _date_label(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def _dir(v: float) -> str:
    return "up" if v > 0 else "down" if v < 0 else "flat"


def _arrow(v: float) -> str:
    return "▲" if v > 0 else "▼" if v < 0 else "–"


def _num(v: float, dec: int) -> str:
    return f"{v:,.{dec}f}"


def _spark(points: list, dec: int, direction: str, quarters: list | None = None, labels: bool = True) -> str:
    """1년 종가 추이 (단일 계열이라 범례 없음). 폭 200 기준 좌표.
    점선 = 분기 경계(아래 1Q~4Q 표시), 마우스/터치하면 날짜·값과 그 분기 시작 대비 현재 등락률을 보여준다."""
    vals = [v for _, v in points]
    if len(vals) < 2:
        return ""
    n = len(vals)
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    h, pad = 44, 3
    xy = [(i / (n - 1) * 200, pad + (hi - v) / span * (h - 2 * pad)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    area = f"0,{h} {line} 200,{h}"
    lx, _ = xy[-1]
    qlines, qlabels, qdata = "", "", []
    for q in quarters or []:
        if not q.get("start"):
            continue
        qdata.append([q["start"], q.get("since", ""), q["pct"]])
        if q["start"] <= points[0][0]:
            continue                                   # 그래프 시작보다 이른 경계는 그리지 않음
        idx = next((i for i, (d, _) in enumerate(points) if d >= q["start"]), None)
        if idx is None:
            continue
        x = idx / (n - 1) * 200
        qlines += f'<line class="qline" x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h}" vector-effect="non-scaling-stroke"/>'
        qlabels += f'<span style="left:{x / 2:.1f}%">{q["label"][-2:]}</span>'
    return (
        f'<div class="spark" data-p="{escape(json.dumps(points))}" data-dec="{dec}" data-q="{escape(json.dumps(qdata, ensure_ascii=False))}">'
        '<span class="tip"></span>'
        f'<svg viewBox="0 0 200 {h}" preserveAspectRatio="none" role="img" aria-label="최근 1년 추이, 최저 {_num(lo, dec)} 최고 {_num(hi, dec)}">'
        f'<polygon points="{area}" fill="var(--{direction}-fill)"/>{qlines}'
        f'<polyline points="{line}" fill="none" stroke="var(--{direction})" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
        f'<line class="guide" x1="{lx:.1f}" x2="{lx:.1f}" y1="0" y2="{h}" vector-effect="non-scaling-stroke"/>'
        "</svg>"
        + (f'<div class="qlabels" aria-hidden="true">{qlabels}</div>' if labels and qlabels else "")
        + "</div>"
    )


def _trend(q: dict) -> float:
    """그래프 색을 정할 기간 수익률 (예전 데이터는 period_pct)."""
    return q.get("y1_pct", q.get("period_pct", 0)) or 0


def _ret(v, label: str = "") -> str:
    if v is None:
        return f'<span class="flat">{label} -</span>' if label else '<span class="flat">-</span>'
    return f'<span class="{_dir(v)}">{label + " " if label else ""}{v:+.2f}%</span>'


def _cap(eok) -> str:
    if not eok:
        return "-"
    return f"{eok / 10000:,.1f}조" if eok >= 10000 else f"{eok:,}억"


def _tile(q: dict) -> str:
    dec = q.get("decimals", 2)
    m1 = q.get("m1_pct", q.get("period_pct"))
    return f"""<div class="tile">
  <span class="grp">{escape(q['group'])}</span>
  <span class="nm">{escape(q['name'])}</span>
  <span class="px">{_num(q['price'], dec)}</span>
  <span class="chg {_dir(q['change'])}">{_arrow(q['change'])} {_num(abs(q['change']), dec)} ({q['change_pct']:+.2f}%)</span>
  {_spark(q.get('spark', []), dec, _dir(_trend(q)), q.get('quarters'))}
  <div class="foot">{_ret(m1, '1개월')}{_ret(q.get('ytd_pct'), '연초 대비')}</div>
</div>"""


def _stocks_table(stocks: list[dict], caption: str) -> str:
    if not stocks:
        return '<p class="empty">시세를 받지 못했습니다.</p>'
    num = lambda v: "" if v is None else v
    rows = []
    for i, s in enumerate(stocks, start=1):
        m1 = s.get("m1_pct", s.get("period_pct"))
        pin = s.get("pinned")
        mine = '<span class="mine">보유</span>' if pin else ""
        rows.append(
            f'<tr{" class=pin" if pin else ""} data-rank="{i}" data-name="{escape(s["name"])}" data-price="{s["price"]}" '
            f'data-chg="{s["change_pct"]}" data-m1="{num(m1)}" data-ytd="{num(s.get("ytd_pct"))}" data-cap="{s.get("cap") or 0}">'
            f'<td><span class="no">{i}</span>{escape(s["name"])}<span class="code">{escape(s["code"])}</span>{mine}</td>'
            f'<td>{_num(s["price"], 0)}</td>'
            f'<td class="{_dir(s["change"])}">{_arrow(s["change"])} {abs(s["change_pct"]):.2f}%</td>'
            f'<td>{_ret(m1)}</td><td>{_ret(s.get("ytd_pct"))}</td>'
            f'<td>{_cap(s.get("cap"))}</td>'
            f'<td class="sp">{_spark(s.get("spark", []), 0, _dir(_trend(s)), s.get("quarters"), labels=False)}</td></tr>'
        )
    return f"""<div class="tablewrap"><table class="sortable">
<caption hidden>{escape(caption)}</caption>
<thead><tr><th data-k="rank">종목</th><th data-k="price">종가(원)</th><th data-k="chg">전일 대비</th><th data-k="m1">1개월</th><th data-k="ytd">연초 대비</th><th data-k="cap">시가총액</th><th>1년 추이</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>"""


def _holdings_html(enc: dict | None) -> str:
    """보유 수익 블록. 암호문만 페이지에 넣고, 숫자는 비밀번호를 넣으면 브라우저가 풀어서 그린다."""
    if not enc:
        return ""
    return f"""<div class="pf" data-enc="{escape(json.dumps(enc))}">
<form class="pf-lock"><span class="t">내 보유 수익<small>평가손익 · 수익률 · 배당금</small></span>
<input type="text" name="username" value="korea-briefing" autocomplete="username" hidden>
<span class="f"><input type="password" name="password" autocomplete="current-password" placeholder="비밀번호" aria-label="비밀번호" required>
<label><input type="checkbox" checked> 이 기기에서 기억</label><button>열기</button></span><span class="err" role="alert"></span></form>
<div class="pf-body" hidden></div></div>"""


def _groups_html(m: dict, enc: dict | None = None) -> str:
    groups = m.get("groups")
    if not groups and m.get("stocks"):          # 예전 데이터: 관심 종목 한 묶음
        groups = [{"name": "관심 종목", "stocks": m["stocks"]}]
    if not groups:
        return ""
    tabs = "".join(
        f'<button data-g="{i}" aria-pressed="{str(i == 0).lower()}">{escape(g["name"])}</button>'
        for i, g in enumerate(groups)
    )
    panels = "".join(
        f'<div class="group" data-g="{i}"{"" if i == 0 else " hidden"}>'
        + (_holdings_html(enc) if g["name"] == HOLDINGS_GROUP else "")
        + f'{_stocks_table(g["stocks"], g["name"] + " 시가총액 상위")}'
        + (f'<p class="note">{escape(g["note"])}</p>' if g.get("note") else "") + "</div>"
        for i, g in enumerate(groups)
    )
    return f"""<h2 class="sec">업종별 TOP {max(len(g['stocks']) for g in groups)}<small>시가총액 순 · 버튼으로 업종 선택 · 머리글을 누르면 정렬</small></h2>
<div class="tabs" role="group" aria-label="업종 선택">{tabs}</div>
{panels}"""


def _market_html(data: dict) -> str:
    m = data.get("market") or {}
    if not m.get("indices") and not m.get("groups") and not m.get("stocks"):
        return ""
    tiles = "".join(_tile(q) for q in m.get("indices", []))
    comment = data.get("market_comment", "")
    md = lambda d: f"{int(d[5:7])}/{int(d[8:])}" if d else ""
    closed, kr = m.get("closed"), md(m.get("kr_date"))
    if closed == "all":
        asof, comment = f"주말·휴일로 새 거래 없음 · {kr} 종가 기준", ""
    elif closed == "kr":
        asof = f"국내 휴장 · 코스피는 {kr} 종가 · 해외는 최근 마감"
    else:
        asof = "전일 종가 기준 · 해외는 최근 마감"
    comment_html = f'<div class="comment"><span class="lbl">시황</span><p>{escape(comment)}</p></div>' if comment else ""
    return f"""<h2 class="sec">시장<small>{asof} · 그래프는 최근 1년, 점선은 분기 경계 · 그래프에 마우스를 올리거나 누르면 분기 시작 대비 등락률</small></h2>
{comment_html}
<div class="tiles">{tiles}</div>
{_groups_html(m, data.get("holdings_enc"))}"""


def _card(s: dict) -> str:
    color = CAT_COLORS.get(s["category"], "#6b7280")
    uniq = list({src["name"]: src for src in reversed(s.get("sources", []))}.values())[::-1][:6]
    sources = "".join(
        f'<a href="{escape(src["link"])}" target="_blank" rel="noopener" title="{escape(src["title"])}">{escape(src["name"])}</a>'
        for src in uniq
    )
    related = "".join(f"<span>{escape(r)}</span>" for r in s.get("related", [])[:3])
    cls = "card top" if s["rank"] == 1 else "card"
    outlets = f'<span title="이 이슈를 보도한 주요 언론사 수">주요 언론 {s["outlets"]}곳</span>' if s.get("outlets") else ""
    return f"""<article class="{cls}" data-cat="{escape(s['category'])}">
  <div class="meta"><span class="rank">{s['rank']:02d}</span><span class="cat" style="background:{color}">{escape(s['category'])}</span>{outlets}</div>
  <h3>{escape(s['title'])}</h3>
  <p class="summary">{escape(s['summary'])}</p>
  <p class="why">{escape(s['why_it_matters'])}</p>
  {f'<div class="related" aria-label="관련 업종·종목">{related}</div>' if related else ''}
  <div class="sources">{sources}</div>
</article>"""


def _digest_html(data: dict, kind: str) -> str:
    """일간·주간·월간 흐름 한 줄씩. kind = "market"(헤더) 또는 "news"(주요 뉴스 위)."""
    today = data.get("market_headline" if kind == "market" else "headline_of_day", "")
    rows = [("일간", today, "")]
    dg = data.get("digest") or {}
    for key, label, span in (("weekly", "주간", 7), ("monthly", "월간", 30)):
        if key in dg:
            n = dg[key]["days"]
            note = f"최근 {span}일" + (f" 중 {n}일치" if n < span else "")
            text = dg[key].get(kind) or (dg[key].get("text", "") if kind == "news" else "")
            rows.append((label, text, note))
    body = "".join(
        f'<div class="row"><span class="lbl">{lbl}</span><p>{escape(text)}'
        + (f'<span class="span">{note}</span>' if note else "") + "</p></div>"
        for lbl, text, note in rows if text
    )
    if not body:
        return ""
    name = "증시 흐름 요약" if kind == "market" else "뉴스 흐름 요약"
    return f'<section class="digest {kind}" aria-label="{name}">{body}</section>'


def render_page(data: dict, d: date, root: str, all_dates: list[date]) -> str:
    counts = Counter(s["category"] for s in data["stories"])
    filters = f'<button data-cat="all" aria-pressed="true">전체<span class="n">{len(data["stories"])}</span></button>' + "".join(
        f'<button data-cat="{escape(c)}" aria-pressed="false">{escape(c)}<span class="n">{counts[c]}</span></button>'
        for c in CATEGORIES if counts[c]
    )
    days = "".join(
        f'<a href="{root}archive/{x.isoformat()}.html">{x.month}/{x.day}</a>'
        for x in sorted(all_dates, reverse=True)[:14] if x != d
    )
    days_html = f'<nav class="days"><a href="{root}index.html">최신</a>{days}</nav>'
    cards = "\n".join(_card(s) for s in data["stories"])
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>국내 뉴스 · 증시 · {d.month}/{d.day}</title>
<meta property="og:title" content="국내 뉴스 · 증시 브리핑 · {_date_label(d)}">
<meta property="og:description" content="{escape(data.get('headline_of_day', ''))}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.min.css">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">Korea Briefing · {_date_label(d)}</div>
  <h1>오늘의 국내 뉴스 · 증시</h1>
  {_digest_html(data, "market")}
  {days_html}
</header>
{_market_html(data)}
<h2 class="sec">주요 뉴스 TOP {len(data['stories'])}</h2>
{_digest_html(data, "news")}
<div class="filters">{filters}</div>
<main class="grid">
{cards}
</main>
<footer>연합뉴스, 한겨레, 경향신문, 동아일보, 조선일보, 매일경제, SBS, JTBC, Google News(종합·경제) RSS를 바탕으로 AI(Google Gemini)가 선정·요약했습니다.
시세는 Yahoo Finance 일별 종가, 시가총액·종목 정보는 네이버 증권 기준이며 지연·오차가 있을 수 있습니다. 투자 판단의 근거로 쓰지 마시고, 정확한 내용은 원문과 공식 시세를 확인하세요.</footer>
</div>
<script>{JS}</script>
</body>
</html>"""


def save_and_render(data: dict, d: date) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    data = {**data, "date": d.isoformat()}
    # 오늘 파일만 그래프 데이터까지 저장. latest.json(카톡 전송용)과 지난 날짜 파일은 그래프 점을 빼서 저장소 용량을 줄인다.
    (DATA_DIR / f"{d.isoformat()}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "latest.json").write_text(json.dumps(_slim(data), ensure_ascii=False, indent=2), encoding="utf-8")
    for p in DATA_DIR.glob("????-??-??.json"):
        if p.stem < d.isoformat():
            old = json.loads(p.read_text(encoding="utf-8"))
            slim = _slim(old)
            if slim != old:
                p.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
    render_all()


def _slim(data: dict) -> dict:
    """그래프용 점(spark)을 뺀 사본. 숫자(종가·등락률·분기 수익률)는 그대로 둔다."""
    m = data.get("market")
    if not m:
        return data
    strip = lambda q: {k: v for k, v in q.items() if k != "spark"}
    m = {**m, "indices": [strip(q) for q in m.get("indices", [])]}
    if "groups" in data["market"]:
        m["groups"] = [{**g, "stocks": [strip(q) for q in g["stocks"]]} for g in data["market"]["groups"]]
    if "stocks" in data["market"]:
        m["stocks"] = [strip(q) for q in data["market"]["stocks"]]
    return {**data, "market": m}


def render_all() -> None:
    files = sorted(p for p in DATA_DIR.glob("????-??-??.json"))
    all_dates = [date.fromisoformat(p.stem) for p in files]
    for p, d in zip(files, all_dates):
        data = json.loads(p.read_text(encoding="utf-8"))
        (ARCHIVE_DIR / f"{d.isoformat()}.html").write_text(
            render_page(data, d, "../", all_dates), encoding="utf-8")
    if files:
        latest = json.loads(files[-1].read_text(encoding="utf-8"))
        (DOCS / "index.html").write_text(
            render_page(latest, all_dates[-1], "", all_dates), encoding="utf-8")
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / ".nojekyll").touch()
    print(f"[render] {len(files)}개 날짜 페이지 생성")
