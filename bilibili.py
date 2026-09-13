"""B站竞品调研抓取工具（公开 API，无需登录）。

用法：
  python bilibili.py search "错题本" [数量]      搜索视频
  python bilibili.py info <bvid>                 视频详情（播放/点赞/投币/收藏/简介）
  python bilibili.py comments <bvid> [数量]      热评
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

_buvid3 = None


def _ensure_buvid3():
    """从 bilibili.com 首页 Set-Cookie 拿匿名标识 buvid3，绕过搜索接口 412 风控。"""
    global _buvid3
    if _buvid3:
        return _buvid3
    req = urllib.request.Request("https://www.bilibili.com/", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        for h in r.headers.get_all("Set-Cookie") or []:
            m = re.search(r"buvid3=([^;]+)", h)
            if m:
                _buvid3 = m.group(1)
                return _buvid3
    return None


def _get(url, need_cookie=False):
    headers = dict(HEADERS)
    if need_cookie:
        buvid3 = _ensure_buvid3()
        if buvid3:
            headers["Cookie"] = f"buvid3={buvid3}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    if data.get("code") != 0:
        raise RuntimeError(f"B站接口错误 code={data.get('code')} message={data.get('message')}")
    return data


def _strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _fmt_time(ts):
    return time.strftime("%Y-%m-%d", time.localtime(ts)) if ts else ""


def search_videos(keyword, limit=10):
    """搜索视频，返回标题/bvid/UP主/播放量/时长/简介。"""
    url = "https://api.bilibili.com/x/web-interface/search/type?" + urllib.parse.urlencode({
        "search_type": "video",
        "keyword": keyword,
        "page": 1,
    })
    data = _get(url, need_cookie=True)
    result = data.get("data", {}).get("result", [])
    videos = []
    for v in result[:limit]:
        videos.append({
            "title": _strip_html(v.get("title")),
            "bvid": v.get("bvid"),
            "author": v.get("author"),
            "play": v.get("play"),
            "duration": v.get("duration"),
            "pubdate": _fmt_time(v.get("pubdate")),
            "description": _strip_html(v.get("description"))[:100],
        })
    return videos


def get_video_info(bvid):
    """视频详情：标题/UP主/发布时间/播放/点赞/投币/收藏/弹幕/简介。"""
    d = _get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")["data"]
    return {
        "title": d.get("title"),
        "bvid": d.get("bvid"),
        "aid": d.get("aid"),
        "author": d.get("owner", {}).get("name"),
        "pubdate": _fmt_time(d.get("pubdate")),
        "desc": _strip_html(d.get("desc"))[:200],
        "stat": {
            "view": d.get("stat", {}).get("view"),
            "like": d.get("stat", {}).get("like"),
            "coin": d.get("stat", {}).get("coin"),
            "favorite": d.get("stat", {}).get("favorite"),
            "danmaku": d.get("stat", {}).get("danmaku"),
        },
    }


def get_comments(bvid, limit=20):
    """热评：用户名/内容/点赞数。"""
    aid = get_video_info(bvid)["aid"]
    data = _get(f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&sort=2&ps={limit}")
    replies = data.get("data", {}).get("replies") or []
    return [
        {
            "user": r.get("member", {}).get("uname"),
            "content": r.get("content", {}).get("message"),
            "like": r.get("like"),
        }
        for r in replies[:limit]
    ]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    try:
        if cmd == "search":
            keyword = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            out = search_videos(keyword, limit)
        elif cmd == "info":
            out = get_video_info(sys.argv[2])
        elif cmd == "comments":
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            out = get_comments(sys.argv[2], limit)
        else:
            print(__doc__)
            sys.exit(1)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)
