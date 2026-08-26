const state = {payload: null, active: 'china'};
const flags = {china:'🇨🇳', usa:'🇺🇸', pakistan:'🇵🇰', india:'🇮🇳'};
const nativeLabels = {china:'3128B 指数', usa:'期货收盘价', pakistan:'Ex-Gin 出厂价', india:'Shankar 6 平均价'};
const order = ['china','usa','pakistan','india'];
const $ = (selector) => document.querySelector(selector);
const money = (value) => new Intl.NumberFormat('zh-CN',{maximumFractionDigits:0}).format(value);
const native = (value) => new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2}).format(value);

function latest(rows){ return rows && rows.length ? rows[rows.length - 1] : null; }
function change(rows){
  if(!rows || rows.length < 2) return {value:0, pct:0};
  const a=rows[rows.length-2].cny_per_ton, b=rows[rows.length-1].cny_per_ton;
  return {value:b-a,pct:a ? (b-a)/a*100 : 0};
}
function escapeHtml(text){const d=document.createElement('div');d.textContent=text;return d.innerHTML;}
function shortDate(value){const [,m,d]=value.split('-');return `${m}/${d}`;}
function formatTime(value){
  if(!value) return '等待首次数据更新';
  return `更新于 ${new Date(value).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})}`;
}
function renderSummary(){
  $('#summary-strip').innerHTML=order.map(code=>{
    const p=latest(state.payload.data[code]);
    return `<div class="summary-item"><span>${state.payload.markets[code].short}</span><b>${p?money(p.cny_per_ton):'—'}</b><small> 元/吨</small></div>`;
  }).join('');
}
function renderTabs(){
  $('#market-tabs').innerHTML=order.map(code=>`<button class="market-tab ${code===state.active?'active':''}" data-code="${code}">${state.payload.markets[code].short}</button>`).join('');
  document.querySelectorAll('.market-tab').forEach(btn=>btn.addEventListener('click',()=>{state.active=btn.dataset.code;renderTabs();renderMarket();}));
}
function chartSvg(rows,color){
  if(!rows.length) return '';
  const values=rows.map(r=>r.cny_per_ton), min=Math.min(...values), max=Math.max(...values), span=Math.max(max-min,1);
  const W=560,H=155,padX=13,padY=16;
  const pts=values.map((v,i)=>({x:rows.length===1?W/2:padX+i*(W-padX*2)/(rows.length-1),y:padY+(max-v)/span*(H-padY*2)}));
  const line=pts.map((p,i)=>`${i?'L':'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  const area=`${line} L ${pts[pts.length-1].x} ${H} L ${pts[0].x} ${H} Z`;
  const grid=[.2,.5,.8].map(f=>`<line class="grid-line" x1="0" y1="${H*f}" x2="${W}" y2="${H*f}"/>`).join('');
  const dots=pts.map((p,i)=>`<circle class="chart-dot" cx="${p.x}" cy="${p.y}" r="${i===pts.length-1?4:2.8}"/>`).join('');
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="--market-color:${color}">${grid}<path class="trend-area" d="${area}"/><path class="trend-line" d="${line}"/>${dots}</svg>`;
}
function renderMarket(){
  const code=state.active, meta=state.payload.markets[code], rows=state.payload.data[code]||[], p=latest(rows), delta=change(rows);
  if(!p){$('#market-view').innerHTML='<div class="error-box"><b>尚无该市场数据</b><span>请运行每日更新任务后刷新。</span></div>';return;}
  const cls=delta.value>0?'up':delta.value<0?'down':'flat', arrow=delta.value>0?'▲':delta.value<0?'▼':'—';
  const source=p.source_name, note=p.metadata?.fallback?'Investing.com 当前拒绝服务器访问，已自动切换备用行情源。':'';
  const extra=code==='usa'?`<span>加10美分后 <b>${native(p.metadata.landed_cents_lb)} 美分/磅</b></span>`:'';
  $('#market-view').innerHTML=`<article class="price-card" style="--market-color:${meta.color}">
    <div class="card-top"><div class="flag-name"><span class="flag">${flags[code]}</span><div><h2>${meta.name}</h2><p>${meta.grade} · 最近${rows.length}个交易日</p></div></div><span class="change ${cls}">${arrow} ${Math.abs(delta.pct).toFixed(2)}%</span></div>
    <div class="main-price"><strong>${money(p.cny_per_ton)}</strong><span>人民币元 / 吨</span></div>
    <div class="native-line"><span>${nativeLabels[code]} <b>${native(p.native_price)} ${escapeHtml(p.native_unit)}</b></span>${extra}</div>
    <div class="chart-wrap">${chartSvg(rows,meta.color)}</div><div class="date-row">${rows.map(r=>`<span>${shortDate(r.date)}</span>`).join('')}</div>
    ${note?`<p class="warning">${note}</p>`:''}
    <div class="source-row"><span>汇率日期 ${p.metadata?.fx_date||p.date}</span><a href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener">${escapeHtml(source)} ↗</a></div>
  </article>`;
}
function renderComparison(){
  const rows=order.map(code=>({code,p:latest(state.payload.data[code]),m:state.payload.markets[code]})).filter(x=>x.p);
  const max=Math.max(...rows.map(x=>x.p.cny_per_ton));
  $('#comparison').innerHTML=rows.map(x=>`<div class="compare-row"><span>${flags[x.code]} ${x.m.short}</span><div class="bar-track"><div class="bar" style="--bar-color:${x.m.color};width:${Math.max(5,x.p.cny_per_ton/max*100)}%"></div></div><b>${money(x.p.cny_per_ton)}</b></div>`).join('');
}
async function load(){
  try{
    const response=await fetch('/api/prices',{cache:'no-store'}); if(!response.ok) throw new Error(`HTTP ${response.status}`);
    state.payload=await response.json(); $('#update-time').textContent=formatTime(state.payload.updated_at); $('#disclaimer').textContent=state.payload.disclaimer;
    renderSummary();renderTabs();renderMarket();renderComparison();
  }catch(error){$('#market-view').innerHTML=`<div class="error-box"><b>数据载入失败</b><span>${escapeHtml(error.message)}</span></div>`;}
}
const dialog=$('#method-dialog');$('#open-method').addEventListener('click',()=>dialog.showModal());$('#close-method').addEventListener('click',()=>dialog.close());dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});load();
