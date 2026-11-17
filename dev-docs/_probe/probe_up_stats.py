"""最终验证：视频 -> UP主 -> 12+ 视频完整数据（含点赞/投币/收藏），排除源视频。"""
import json, sys, re, time, datetime as dt, tempfile, os
sys.path.insert(0, "/Users/rongziyu/.local/share/uv/tools/bilinote-cli/lib/python3.12/site-packages")
from app.utils.cookie_helper import get_cookie
from app.utils.bilibili_meta import format_number
import yt_dlp
from bilibili_api import user, video, sync

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CK = get_cookie("bilibili")
SRC = "https://www.bilibili.com/video/BV1GJ411x7h7"

# 1) 源视频 -> mid
opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
        "http_headers": {"Referer": "https://www.bilibili.com", "User-Agent": UA}}
fd, cf = tempfile.mkstemp(suffix=".txt")
with os.fdopen(fd, "w") as f:
    f.write("# Netscape HTTP Cookie File\n")
    for it in CK.split(';'):
        it = it.strip()
        if '=' in it:
            n, v = it.split('=', 1)
            f.write(f".bilibili.com\tTRUE\t/\tFALSE\t2147483647\t{n.strip()}\t{v.strip()}\n")
opts["cookiefile"] = cf
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(SRC, download=False)
src_bvid, mid, upname = info["id"], int(info["uploader_id"]), info["uploader"]
print(f"源视频 {src_bvid} -> UP主「{upname}」mid={mid}")

# 2) 空间列表（按播放量），排除源视频
u = user.User(mid, credential=user.Credential(CK) if CK else None)
rows = []
pn = 1
while len(rows) < 12 and pn <= 3:
    d = sync(u.get_videos(pn=pn, ps=30, order=user.VideoOrder.VIEW))
    for v in d.get("list", {}).get("vlist", []):
        if v["bvid"] == src_bvid:
            continue
        rows.append(v)
        if len(rows) >= 12:
            break
    pn += 1
print(f"空间列表取到 {len(rows)} 条（已排除源视频）")

# 3) 逐个补全 stat
final = []
for i, v in enumerate(rows, 1):
    bv = v["bvid"]
    try:
        st = sync(video.Video(bvid=bv, credential=CK and video.Credential(CK)).get_info()).get("stat", {})
    except Exception as e:
        st = {}
        print(f"  [{i}] stat 失败 {bv}: {type(e).__name__}")
    time.sleep(0.35)
    final.append({
        "rank": i, "bvid": bv,
        "title": re.sub(r'<[^>]+>', '', v["title"]),
        "play": st.get("view", v.get("play")),
        "like": st.get("like"), "coin": st.get("coin"),
        "favorite": st.get("favorite"), "danmaku": st.get("danmaku"),
        "reply": st.get("reply", v.get("comment")),
        "length": v.get("length"),
        "pubdate": dt.datetime.fromtimestamp(v["created"]).strftime("%Y-%m-%d"),
        "url": f"https://www.bilibili.com/video/{bv}",
    })

print(f"\n{'#':>2} {'播放':>8} {'点赞':>7} {'投币':>7} {'收藏':>7} {'弹幕':>6} {'评论':>6} {'时长':>6}  发布        标题")
print("-" * 122)
for r in final:
    print(f"{r['rank']:>2} {format_number(r['play']):>8} {format_number(r['like']):>7} {format_number(r['coin']):>7} "
          f"{format_number(r['favorite']):>7} {format_number(r['danmaku']):>6} {format_number(r['reply']):>6} "
          f"{r['length']:>6}  {r['pubdate']}  {r['title'][:38]}")

json.dump({"up": {"name": upname, "mid": mid}, "videos": final},
          open("/tmp/bilitest/final.json","w"), ensure_ascii=False, indent=2)
print("\n完整数据 -> /tmp/bilitest/final.json")
