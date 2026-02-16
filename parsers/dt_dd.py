"""dt/ddパターンの汎用パーサー"""

import re
import socket
import ipaddress
import urllib.request
import urllib.parse

_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_url(url: str) -> None:
    """URLの安全性を検証する"""
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r} (only http/https allowed)")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"No hostname in URL: {url!r}")

    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname!r}")

    for _family, _, _, _, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError(
                f"Access to private/reserved IP is forbidden: {hostname} -> {ip}"
            )


def fetch_html(url: str, timeout: int = 15) -> str:
    """URLからHTMLを取得"""
    _validate_url(url)

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    data = resp.read(_MAX_RESPONSE_BYTES + 1)
    if len(data) > _MAX_RESPONSE_BYTES:
        raise ValueError(
            f"Response exceeds size limit ({_MAX_RESPONSE_BYTES // (1024 * 1024)} MB)"
        )
    return data.decode("utf-8", errors="replace")


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
