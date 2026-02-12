"""dt/ddパターンの汎用パーサー"""

import re
import urllib.request


def fetch_html(url: str, timeout: int = 15) -> str:
    """URLからHTMLを取得"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="replace")


def extract_ids(html: str, pattern: str) -> list:
    """HTMLからID一覧を正規表現で抽出（重複除去、順序保持）"""
    ids = re.findall(pattern, html)
    seen = set()
    unique = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    return unique


def parse_dt_dd(html: str) -> dict:
    """dt/ddペアをkey-valueのdictとして抽出"""
    pairs = re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", html, re.DOTALL)
    data = {}
    for key, val in pairs:
        # タグ除去
        key = re.sub(r"<[^>]+>", "", key).strip()
        val = re.sub(r"<br\s*/?>", "\n", val)
        val = re.sub(r"<[^>]+>", "", val)
        val = re.sub(r"\n{2,}", "\n", val).strip()
        if key and key not in data:
            data[key] = val
    return data


def parse_meta(html: str, meta_patterns: dict = None) -> dict:
    """タイトル、ID、更新日等のメタ情報を抽出"""
    meta = {}
    defaults = {
        "title": r"<title[^>]*>(.*?)</title>",
    }
    patterns = {**defaults, **(meta_patterns or {})}
    for key, pat in patterns.items():
        m = re.search(pat, html, re.DOTALL)
        if m:
            val = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            meta[key] = val
    return meta
