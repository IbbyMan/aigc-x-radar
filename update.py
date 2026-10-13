#!/usr/bin/env python3
"""AIGC X Radar 数据更新脚本.
用法:
  X_BEARER_TOKEN=xxx python3 update.py            # 通过 X API v2 重新抓取并生成 data.json
  python3 update.py --from-raw raw.json           # 用已有原始数据重新生成 data.json
"""
import json, os, sys, re, datetime, urllib.request, urllib.parse, time
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo("Asia/Shanghai")
API = os.environ.get("X_API_ENDPOINT", "https://api.x.com/2/tweets/search/all")  # 无全量权限可改 /2/tweets/search/recent
DAYS = int(os.environ.get("RADAR_DAYS", "21"))
QUOTE_N = 3
FIELDS = {
    "max_results": "25", "sort_order": "relevancy",
    "tweet.fields": "possibly_sensitive,created_at,public_metrics,author_id,conversation_id,referenced_tweets,attachments,lang",
    "expansions": "author_id,attachments.media_keys,referenced_tweets.id,referenced_tweets.id.author_id",
    "user.fields": "username,name,description,public_metrics,verified",
    "media.fields": "type,url,preview_image_url",
}
QUERIES = [
    '"pencil test" (Ariel OR "Little Mermaid" OR AI) -is:retweet',
    '大肥鱼 -is:retweet',
    '("sword cat" OR "drool cat" OR "@_numanuk") has:media -is:retweet',
    '(背篓 OR 原生家庭) (AI OR 短片 OR 视频) -is:retweet',
    '"rocket cat" has:media -is:retweet',
    '(西游记 纽约) OR ("Journey to the West" "New York") OR (Wukong "New York")',
    '(大肥鱼 OR 火箭猫 OR 悟空 AI OR 八戒 AI OR "师父") (AI OR 视频) -is:retweet',
    '("AI short film" OR "AI generated" OR "made with AI" OR "AI video") (viral OR views OR million) has:videos -is:retweet -is:reply',
    '(AI短片 OR AI动画 OR AI短剧 OR AI漫剧 OR AI视频 爆火 OR AI二创) -is:retweet -is:reply',
    '("AI trailer" OR "AI music video" OR "AI MV" OR "AI animated series" OR "AI anime" OR "episode 1") has:videos -is:retweet -is:reply',
    '(AI cat OR "cat video" OR kitten) (AI OR "AI generated") has:videos -is:retweet -is:reply',
    '(AI parody OR "AI remake" OR "but it\'s AI" OR "real life") (AI) has:videos -is:retweet -is:reply',
    '("LEGO" "AI music video") OR (MAKOTO "AI anime") OR ("in real life" cartoon AI) has:videos -is:retweet',
    '("hit" OR "reached" OR "gained") ("M views" OR "million views") (AI OR "AI-generated") has:videos -is:retweet -is:reply',
    '("AI short film" OR "AI short" OR "AI film") (story OR episode OR emotional OR horror OR comedy) has:videos -is:retweet -is:reply',
    '("Jean Phil" OR "Edna Mode" OR "AI influencer" OR "AI character") (views OR viral OR Instagram) -is:retweet -is:reply',
    '(MAKOTO OR "AI anime" OR "AIアニメ" OR "AI animation") (episode OR 第1話 OR series) -is:retweet -is:reply',
    '("would call this AI" OR "looks like AI" OR "thought it was AI" OR "is this AI") has:videos -is:retweet -is:reply',
]
QUOTE_ORIGINS = 3  # 每次自动对热度最高的 N 个簇首发帖调用 quote_tweets 接口拉取真实引用链
# 簇 = 一部作品 / 一种梗格式。字段: id, 标题, 摘要, 匹配正则, 爆款拆解(hook/format/style/why)
CLUSTERS = [
    ("rocketcat", "Rocket Cat 火箭猫 & @_numanuk 动物梗宇宙", "一只头戴钢盔、扛火箭筒的小猫短视频（@_numanuk 首发）。几小时内衍生出无数配文二创、表情贴纸；同作者的「Catana / Sword Cat」持刀猫也被重新翻红，形成「AI 动物梗宇宙」。",
     r"rocket ?cat|rocketcat|bazucat|bomba ?cat|火箭猫|sword ?cat|catana|drool cat|ai animal",
     {"hook": "萌物 × 重武器的反差：最可爱的脸 + 最离谱的火力", "format": "几秒无台词循环短片，零语言门槛，可配任意文案", "style": "写实质感萌宠 + 战场烟雾特效", "why": "极易套梗（「会议结束」「清场」），被二创账号批量配文，再被 meme 币社区二次放大"}),
    ("ariel", "Ariel 铅笔稿真假反转", "一段「小美人鱼 Ariel 铅笔动画稿 → 彩色成片」对比视频被当作「AI 把铅笔稿上色」疯传；10-12 @knightama 揭晓反转：铅笔稿才是 AI 生成的，彩色版是原片。评论区「你被骗了」大战。",
     r"pencil test",
     {"hook": "「AI 能把铅笔稿变成迪士尼成片？」→ 反转：铅笔稿才是 AI", "format": "左右/前后对比视频 + 揭晓帖", "style": "经典 2D 手绘动画质感", "why": "真假辨别激发站队；揭晓帖制造第二波传播，引用与回复里大量「我早看出来了」"}),
    ("xiyou", "西游记 AI 新编：西游记在纽约", "把《西游记》角色丢进现代都市与跨界设定：悟空在曼哈顿大战灭霸、「师父购物，徒儿护驾」、悟空穿过时代广场、八戒误入唐人街。",
     r"西游|悟空|八戒|蜘蛛精|女仆|猫耳|唐僧|师父购物|wukong|journey to the west|三蔵",
     {"hook": "国民 IP × 错位时空：取经团出现在曼哈顿 / 时代广场 / 唐人街", "format": "电影感短片 + 一句话设定文案（「当西游记在纽约醒来」）", "style": "写实摄影风、摩天楼与霓虹都市夜景、跨界大战", "why": "IP 自带认知、东西方反差设定天然好奇；中文圈转推矩阵集中转发，日语圈也有偶像化二创"}),
    ("fatfish", "「大肥鱼」宇宙：APT 合唱 → 打工人日常连载", "中文圈爆梗：DeepSeek 拟人形象「大肥鱼」先以与梁文锋合唱 APT 的 AI 视频出圈；10-12 起 @Remake___ 连更「大肥鱼的一天」（摆摊 14 小时、10 平米出租屋、抱着电饭煲睡着），延伸出「AI 界原生家庭」等拟人梗。",
     r"大肥鱼|梁圣|原生家庭最|ai界原生家庭",
     {"hook": "可爱拟人吉祥物 × 打工人心酸日常", "format": "按时间点连更的图文/短视频（「晚上十点，大肥鱼…」）", "style": "萌系拟人 + 生活流", "why": "社畜共鸣 + 连载追更；圈内 AI 产品互黑梗（被 Claude/GPT 抢饭）提供无限素材"}),
    ("lego", "LEGO AI Music Video 政治讽刺 MV 系列", "@drew_ponder 持续发布的乐高风格 AI 音乐视频，以时政人物为主角的讽刺 MV，形成固定栏目。",
     r"lego.{0,30}music video|lego ai",
     {"hook": "乐高小人演绎时政热点", "format": "系列化 MV，固定标题后缀", "style": "乐高定格动画质感", "why": "时事热点 + 统一品牌化包装，便于粉丝追更与站队转发"}),
    ("aichar", "AI 虚拟角色走红：Edna Mode 真人版 / Jean Phil", "AI 生成的「真人版卡通角色」与虚拟人账号在 IG / X 上两天涨粉数万、播放破千万，引发「AI 角色能否成为网红」讨论。",
     r"jean phil|edna mode|ai character|ai influencer|ai girl|cartoon character",
     {"hook": "卡通角色「真人化」/ 一张有辨识度的脸", "format": "角色日更短视频（街头、日常）", "style": "超写实街拍", "why": "强记忆点人设 + 跨平台搬运，数据截图本身成为二次传播素材"}),
    ("anime", "AI 动画 / 连载剧集", "以「第 1 集」形式连载的 AI 动画与同人剧集，如《MAKOTO》第 1 話、哈利波特同人连载等。",
     r"makoto|ai anime|aiアニメ|ai animation|episode \d|第1話",
     {"hook": "「史上最强 AI 动画」式宣言 + 连载悬念", "format": "按集发布，双语标题", "style": "日系赛璐璐 / 同人剧照风", "why": "追更机制带来回访，同人 IP 吸引原作粉"}),
    ("shorts", "原创 AI 叙事短片：《Onyx》《SALT》等", "个人创作者发布的完整叙事短片：「爱死机」风克苏鲁科幻《Onyx》、情感短片《SALT》《The Space Beside Me》、28 分钟长片等。",
     r"short film|ai movie|ai film|爱死机|onyx|ai短片|ai 短片|分镜",
     {"hook": "「一个人 + 十天 = 一部短片」的创作者叙事", "format": "1–30 分钟完整剧情片", "style": "电影感、科幻/情感题材", "why": "完成度与工作量本身就是卖点；创作者圈互相引用"}),
]
# 严格 NSFW 过滤：关键词(中英) + X API possibly_sensitive + 屏蔽账号(简介/名称含成人向词)
NSFW_RE = re.compile(r"nsfw|sexy|sexi|hot girl|bikini|lingerie|onlyfans|only fans|fansly|18\+|r18|porn|xxx|nude|naked|boob|busty|thicc|cleavage|pantyhose|stocking|lewd|hentai|ecchi|bdsm|spank|slave|fetish|erotic|seductive|horny|cosplay girl|waifu|ai girl|maid|"
    r"福利|擦边|性感|美女|涩|色色|色情|黄片|裸|内衣|丝袜|巨乳|诱惑|情色|成人|大尺度|洗澡|没有穿衣服|不穿|蜘蛛精|女仆|猫耳|エロ|えっち|セクシー|水着|下着", re.I)
BLOCK_AUTHORS = {"easonnli", "easonnll", "smax_bdsm", "aiexoticdotcom", "renzo_beat", "hot_lalisa27", "capitalatlasq", "umka444444", "linerscott87111", "craftlightmagic"}
# 人工复核后隐藏缩略图的帖子（帖子保留，仅不显示媒体；宁可错杀）
HIDE_MEDIA = {"2109642398179758311", "2109687535186424189"}
def is_nsfw(p, u):
    if p.get("possibly_sensitive"): return True
    if u.get("username", "").lower() in BLOCK_AUTHORS: return True
    return bool(NSFW_RE.search(p.get("text", "") + " " + json.dumps(p.get("article", {}), ensure_ascii=False)) or NSFW_RE.search(u.get("name", "") or "") or NSFW_RE.search(u.get("description", "") or ""))

# 可选: 簇成员还须命中的正则（排除无关提及）
MUST = {"xiyou": r"\bAI\b|AI|seedance|H3|prompt|作品|生成", "anime": r"AI|ＡＩ", "aichar": r"AI|character|角色"}
EXCLUDE = re.compile(r"coin|onboard|business|systems?\b|\$\$|token|launch(ed)? on|CA:|inference|zevio|memecoin|meme coin|onchain|\bbid\b|\bmeta\b|retard|dumbass|crypto|#ad\b|paidpartnership", re.I)
SPAM_RE = re.compile(r"tokens/sec|coding model|pump|\$[A-Za-z]{3,}|0x[0-9a-f]{20}|airdrop|bdsm|slave|nsfw|pantyhose|色情|porn|open source|收益|赚|\$\d|per month|/month|monetiz|portfolio", re.I)

def fetch():
    tok = os.environ.get("X_BEARER_TOKEN")
    if not tok: sys.exit("缺少环境变量 X_BEARER_TOKEN")
    start = (datetime.datetime.utcnow() - datetime.timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts, users, media = {}, {}, {}
    for q in QUERIES:
        params = dict(FIELDS, query=q, start_time=start)
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"Authorization": "Bearer " + tok})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            print("query failed:", q, e); continue
        inc = d.get("includes", {})
        for u in inc.get("users", []): users[u["id"]] = u
        for m in inc.get("media", []): media[m["media_key"]] = m
        for p in d.get("data", []) + inc.get("tweets", []): posts.setdefault(p["id"], p)
        time.sleep(2.5)  # 速率限制
    raw = {"posts": posts, "users": users, "media": media}
    # 拉取头部原帖的引用链
    tops = sorted(posts.values(), key=lambda p: -eng(p.get("public_metrics", {})))[:QUOTE_ORIGINS * 3]
    for p in tops[:QUOTE_ORIGINS]:
        url = f"https://api.x.com/2/tweets/{p['id']}/quote_tweets?" + urllib.parse.urlencode({k: v for k, v in FIELDS.items() if k not in ("sort_order",)})
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=30))
            for u in d.get("includes", {}).get("users", []): users[u["id"]] = u
            for m in d.get("includes", {}).get("media", []): media[m["media_key"]] = m
            for q in d.get("data", []): posts.setdefault(q["id"], q)
        except Exception as e: print("quotes failed", p["id"], e)
        time.sleep(2.5)
    json.dump(raw, open(os.path.join(HERE, "raw.json"), "w"))
    return raw

def eng(m):
    return m.get("like_count",0) + 2*m.get("retweet_count",0) + 3*m.get("quote_count",0) + m.get("reply_count",0) + m.get("bookmark_count",0)

def local(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(TZ).strftime("%Y-%m-%d %H:%M")

def build(raw, summaries=None):
    U, M = raw["users"], raw["media"]
    out = []
    for p in raw["posts"].values():
        u = U.get(p.get("author_id"), {})
        if not u.get("username") or p["text"].startswith("RT @") or SPAM_RE.search(p["text"]) or u["username"] == "grok" or is_nsfw(p, u): continue
        pm = dict(p.get("public_metrics", {})); pm.setdefault("retweet_count", pm.get("repost_count", 0))
        thumbs = []
        for k in ([] if p["id"] in HIDE_MEDIA else p.get("attachments", {}).get("media_keys", [])):
            m = M.get(k, {}); t = m.get("url") or m.get("preview_image_url")
            if t: thumbs.append({"src": t, "type": m.get("type")})
        out.append({"id": p["id"], "url": f"https://x.com/{u['username']}/status/{p['id']}",
            "author": u["username"], "name": u.get("name"), "followers": u.get("public_metrics",{}).get("followers_count",0),
            "created_at": p["created_at"], "time_local": local(p["created_at"]),
            "text": re.sub(r"https://t\.co/\S+$", "", p["text"]).strip(), "metrics": pm, "engagement": eng(pm),
            "media": thumbs[:2], "refs": p.get("referenced_tweets", [])})
    byid = {p["id"]: p for p in out}
    clusters, used = [], set()
    for cid, title, desc, rx, brk in CLUSTERS:
        r = re.compile(rx, re.I)
        mr = re.compile(MUST.get(cid, "."), re.I)
        mem = [p for p in out if p["id"] not in used and r.search(p["text"]) and mr.search(p["text"]) and not EXCLUDE.search(p["text"])]
        # 引用了簇内帖子的引用帖也归入该簇（真实引用链）
        ids = {p["id"] for p in mem}
        mem += [p for p in out if p["id"] not in used and p["id"] not in ids and any(x["type"]=="quoted" and x["id"] in ids for x in p["refs"])]
        if len(mem) < 2: continue
        used |= {p["id"] for p in mem}
        mem.sort(key=lambda p: p["created_at"])
        top = sorted(mem, key=lambda p: -p["engagement"])
        origin = next(p for p in mem if p["engagement"] >= 0.05 * top[0]["engagement"])
        total = sum(p["engagement"] for p in mem)
        heat = round(100 * (1 - 1/(1 + total/400)), 1)
        peak = top[0]
        ids = {p["id"] for p in mem}
        quotes = [p for p in mem if any(x["type"]=="quoted" and x["id"] in ids for x in p["refs"])]
        def stage(p):
            q = next((x["id"] for x in p["refs"] if x["type"]=="quoted" and x["id"] in byid), None)
            if p["author"] == origin["author"]: return "原作者续作" if not q else "原作者自引用"
            if q: return "引用二创 ← @" + byid[q]["author"]
            return "KOL 跟进" if p["followers"] > 10000 else "二创/仿作"
        cand = [p for p in mem if p["id"] not in (origin["id"], peak["id"]) and p["created_at"] >= origin["created_at"]]
        picks, seen = [], {origin["author"], peak["author"]}
        for p in sorted(cand, key=lambda p: -(p["engagement"] + (300 if p in quotes else 0) + p["followers"]/200)):
            if p["author"] in seen and len(set(x["author"] for x in mem)) > 3: continue
            seen.add(p["author"]); picks.append(p)
            if len(picks) == 4: break
        tl = [{"stage": "源头", **pick(origin)}] + [{"stage": stage(p), **pick(p)} for p in picks]
        if peak["id"] != origin["id"]: tl.append({"stage": "峰值", **pick(peak)})
        tl.sort(key=lambda x: x["created_at"])
        remixes = sorted([p for p in mem if p["id"] != origin["id"] and p["author"] != origin["author"]], key=lambda p: -p["engagement"])[:6]
        clusters.append({"id": cid, "title": title, "summary": desc, "breakdown": brk, "heat": heat, "engagement_total": total,
            "post_count": len(mem), "quote_count": len(quotes), "impressions": sum(p["metrics"].get("impression_count",0) for p in mem),
            "first": origin["time_local"], "peak": peak["time_local"], "origin": pick(origin) | {"media": origin["media"], "metrics": origin["metrics"]},
            "posts": top[:6], "timeline": tl, "remixes": remixes})
    clusters.sort(key=lambda c: -c["heat"])
    now = datetime.datetime.now(TZ)
    data = {"generated_at": now.strftime("%Y-%m-%d %H:%M"), "data_date": now.strftime("%Y-%m-%d"), "timezone": "Asia/Shanghai",
        "window_days": DAYS, "total_posts": len(out), "queries": QUERIES, "clusters": clusters}
    json.dump(data, open(os.path.join(HERE, "data.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "data.js"), "w") as f:
        f.write("window.RADAR_DATA = " + json.dumps(data, ensure_ascii=False) + ";")
    print(f"posts={len(out)} clusters={len(clusters)}")
    return data

def pick(p):
    return {k: p[k] for k in ("id","url","author","followers","created_at","time_local","engagement","text")} | {"text": p["text"][:120]}

if __name__ == "__main__":
    summ_path = os.path.join(HERE, "summaries_zh.json")
    summ = json.load(open(summ_path)) if os.path.exists(summ_path) else {}
    if "--from-raw" in sys.argv:
        raw = json.load(open(sys.argv[sys.argv.index("--from-raw")+1]))
    else:
        raw = fetch()
    build(raw, summ)
