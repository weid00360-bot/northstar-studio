#!/usr/bin/env python3
"""
自动 cookie 提取 —— 用户只要在浏览器登录抖音,agent 自动拿 cookie,不用手抠。

原理:从浏览器本地 cookie 库读 douyin.com 的登录态(browser_cookie3)。
验证过:Chrome 可读到 sessionid/sid_guard 等,直连 creator.douyin.com 底表 200。
macOS 首次读 Chrome 可能弹一次钥匙串授权("访问 Chrome Safe Storage")→ 点允许即可。

优先级:Chrome族(Chrome/Edge/Brave/Arc/Chromium) → Safari → 手动兜底(~/.douyin_cookie)。
"""
import sys
from pathlib import Path

# 判断 cookie 是否含登录态(否则等于没登录)
_AUTH_KEYS = {"sessionid", "sessionid_ss", "sid_guard"}
MANUAL_FILE = Path("~/.douyin_cookie").expanduser()


def _jar_to_str(cj):
    return "; ".join(f"{c.name}={c.value}" for c in cj)


def _has_auth(cj):
    return bool({c.name for c in cj} & _AUTH_KEYS)


def from_browser(domain="douyin.com"):
    """遍历常见浏览器,返回第一个含登录态的 cookie 串。失败返回 None。"""
    try:
        import browser_cookie3 as bc
    except ImportError:
        print("⚠️ 未装 browser_cookie3(pip install browser_cookie3),转手动 cookie。", file=sys.stderr)
        return None
    loaders = [
        ("Chrome", bc.chrome), ("Edge", bc.edge), ("Brave", bc.brave),
        ("Arc", getattr(bc, "arc", None)), ("Chromium", bc.chromium),
        ("Safari", bc.safari), ("Firefox", bc.firefox),
    ]
    for name, fn in loaders:
        if fn is None:
            continue
        try:
            cj = fn(domain_name=domain)
            if _has_auth(cj):
                print(f"✓ 从 {name} 自动读取到抖音登录态", file=sys.stderr)
                return _jar_to_str(cj)
        except Exception:
            continue  # 该浏览器没装/没登录/读不了,试下一个
    return None


def from_manual():
    if MANUAL_FILE.exists():
        s = MANUAL_FILE.read_text().strip()
        if s:
            print(f"✓ 用手动 cookie({MANUAL_FILE})", file=sys.stderr)
            return s
    return None


def get_cookie(prefer_browser=True):
    """拿一把可用 cookie。优先自动读浏览器,兜底手动文件。"""
    cookie = (from_browser() if prefer_browser else None) or from_manual()
    if not cookie:
        raise SystemExit(
            "❌ 拿不到抖音 cookie。请在 Chrome/Edge 登录 creator.douyin.com,"
            "或把 cookie 存到 ~/.douyin_cookie。")
    return cookie


if __name__ == "__main__":
    c = get_cookie()
    print(f"cookie 长度 {len(c)},含登录态 {'sessionid' in c}")
