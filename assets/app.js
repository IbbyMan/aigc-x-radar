const D=window.RADAR_DATA;const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const k=n=>n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(1)+'K':n;
$('#datePill').textContent='DATA '+D.data_date;
const nPosts=D.clusters.reduce((a,c)=>a+c.post_count,0);
$('#stats').innerHTML=[[D.clusters.length,'热点内容簇'],[nPosts,'归类帖子'],[D.total_posts,'检索帖子(过滤后)'],[D.clusters.reduce((a,c)=>a+c.quote_count,0),'真实引用链']].map(([v,l])=>`<div class="stat"><b>${v}</b><span>${l}</span></div>`).join('');

const mx=f=>Math.max(...D.clusters.map(f));
const hrs=c=>{const a=new Date(c.first.replace(' ','T')),b=new Date(c.peak.replace(' ','T'));return Math.max(1,(b-a)/36e5)};
function standStats(c){return[['破坏力',c.heat/100],['速度',Math.min(1,24/hrs(c)+.15)],['射程',Math.log1p(c.impressions)/Math.log1p(mx(x=>x.impressions))],['持续力',c.post_count/mx(x=>x.post_count)],['二创力',Math.min(1,(c.remixes.length+c.quote_count)/16)]]}
const grade=v=>v>=.85?'A':v>=.65?'B':v>=.45?'C':v>=.25?'D':'E';
function standBlock(c,S){const n=S.length,R=52,cx=75,cy=75,pt=(i,r)=>{const a=-Math.PI/2+i*2*Math.PI/n;return[cx+r*Math.cos(a),cy+r*Math.sin(a)]};
const ring=f=>S.map((_,i)=>pt(i,R*f).join(',')).join(' ');
const poly=S.map(([,v],i)=>pt(i,R*Math.max(.12,v)).join(',')).join(' ');
const lbls=S.map(([l],i)=>{const[x,y]=pt(i,R+14);return`<text class="lbl" x="${x}" y="${y+4}" text-anchor="middle">${grade(S[i][1])}</text>`}).join('');
return `<div class="stand"><svg viewBox="0 0 150 150"><polygon points="${ring(1)}" fill="#1a0e28" stroke="#9b30ff" stroke-width="2"/><polygon points="${ring(.66)}" fill="none" stroke="#3a2356"/><polygon points="${ring(.33)}" fill="none" stroke="#3a2356"/>
<polygon points="${poly}" fill="rgba(255,43,214,.55)" stroke="#ffd400" stroke-width="2.5"/>${lbls}</svg>
<div class="bars"><div class="heatnum">${c.heat}<small>HEAT / 替身能力</small></div>${S.map(([l,v])=>`<div class="bar-row"><span>${l}</span><div class="b"><i style="width:${Math.round(v*100)}%"></i></div><em>${grade(v)}</em></div>`).join('')}</div></div>`}
const post=p=>`<a class="post" href="${p.url}" target="_blank"><div class="h"><span><b>@${esc(p.author)}</b> · ${p.time_local}</span><span>♥ ${k(p.metrics.like_count)} · ⟲ ${k(p.metrics.retweet_count)} · 👁 ${k(p.metrics.impression_count||0)}</span></div><div class="t">${esc(p.text)}</div></a>`;
$('#clusterGrid').innerHTML=D.clusters.map((c,i)=>{const th=c.posts.flatMap(p=>p.media.map(m=>({...m,url:p.url}))).slice(0,3);
const S=standStats(c);return `<article class="card"><span class="rank">#${i+1}</span><div class="meta"><span class="tag">${c.post_count} 帖</span><span class="tag">互动 ${k(c.engagement_total)}</span><span class="tag">曝光 ${k(c.impressions)}</span></div>
<h3>${esc(c.title)}</h3><p>${esc(c.summary)}</p>${standBlock(c,S)}
${th.length?`<div class="thumbs">${th.map(m=>`<a href="${m.url}" target="_blank" class="${m.type!=='photo'?'v':''}"><img loading="lazy" src="${m.src}" alt=""></a>`).join('')}</div>`:''}
<div class="plist">${c.posts.slice(0,3).map(post).join('')}</div></article>`}).join('');
$('#routeList').innerHTML=D.clusters.map(c=>`<div class="route"><h3>${esc(c.title)}<span class="tag">首发 ${c.first}</span><span class="tag mag">峰值 ${c.peak}</span></h3><div class="tl">${c.timeline.map(s=>`<div class="step ${s.stage==='峰值'?'peak':s.stage==='源头'?'first':''}"><div class="s">${s.stage}${s.stage==='源头'&&s.id===c.posts[0].id?' · 即峰值':''}</div><div class="d">${s.time_local} · 互动 ${k(s.engagement)} · 粉丝 ${k(s.followers)}</div><a href="${s.url}" target="_blank"><b>@${esc(s.author)}</b> ${esc(s.text)}</a></div>`).join('')}</div></div>`).join('');
$('#remixList').innerHTML=D.clusters.map(c=>`<div class="route"><h3>${esc(c.title)}<span class="tag tox">源头 @${esc(c.origin.author)}</span><span class="tag">二创 ${c.remixes.length} · 引用链 ${c.quote_count}</span></h3><div class="tech">${c.remixes.map(p=>`<a class="tcard" href="${p.url}" target="_blank">${p.media[0]?`<div class="thumbs" style="grid-template-columns:1fr"><span style="aspect-ratio:16/9;display:block;overflow:hidden;border:3px solid #000"><img loading="lazy" src="${p.media[0].src}" style="width:100%;height:100%;object-fit:cover"></span></div>`:''}<div class="orig">${esc(p.text)}</div><div class="f"><span><b>@${esc(p.author)}</b> · ${p.time_local}</span><span class="tag mag">♥${k(p.metrics.like_count)} ⟲${k(p.metrics.retweet_count)}</span></div></a>`).join('')||'<div class="orig">暂无他人二创样本</div>'}</div></div>`).join('');
$('#whyList').innerHTML=D.clusters.map(c=>{const b=c.breakdown;return `<div class="tcard"><div class="zh" style="color:var(--gold);font-family:var(--f-cjk);font-weight:400;font-size:18px">${esc(c.title)}</div>${[['HOOK 钩子',b.hook],['FORMAT 形式',b.format],['STYLE 风格',b.style],['WHY 为什么会传',b.why]].map(([l,v])=>`<div class="why"><span class="tag tox">${l}</span><div>${esc(v)}</div></div>`).join('')}<div class="f"><span>源头 <b>@${esc(c.origin.author)}</b> · ${c.first}</span><a class="tag gold" href="${c.origin.url}" target="_blank">看源头 ↗</a></div></div>`}).join('');
$('#dailyInfo').innerHTML=`<div class="kv"><span class="tag tox">数据日期 ${D.data_date} (${D.timezone})</span><span class="tag">生成于 ${D.generated_at}</span><span class="tag">时间窗 ≈ 近 ${D.window_days} 天</span><span class="tag">${D.queries.length} 组检索词</span></div><p style="color:var(--sub);line-height:1.7">页面读取 <code>data.js</code>（与 <code>data.json</code> 同内容，便于 file:// 直接打开）。运行 <code>update.py</code> 即可调用 X API v2 重新抓取、聚类、计算热度并重新生成数据；可配合 cron 每日 09:00 (Asia/Shanghai) 执行。</p>`;
