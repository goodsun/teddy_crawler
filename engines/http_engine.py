"""HTTP Engine — SSRサイト用クローラーエンジン"""

import json
import time
import yaml
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.dt_dd import fetch_html, extract_ids, parse_dt_dd, parse_meta
from core.schema import normalize, empty_record


def load_site_config(config_path: str) -> dict:
    """サイト設定YAMLを読み込み"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def crawl_list_pages(config: dict, max_pages: int = None) -> list:
    """一覧ページを巡回してID一覧を取得"""
    list_url = config["list_url"]
    id_pattern = config["id_pattern"]
    base_url = config.get("base_url", "")
    page_param = config.get("page_param", "p")
    start_page = config.get("start_page", 1)
    end_page = config.get("end_page", 1)
    delay = config.get("delay", 1.0)

    if max_pages:
        end_page = min(end_page, start_page + max_pages - 1)

    all_ids = []
    seen = set()

    for page in range(start_page, end_page + 1):
        url = f"{base_url}{list_url}".replace("{page}", str(page))
        print(f"📄 Page {page}/{end_page}: {url}")

        try:
            html = fetch_html(url)
            ids = extract_ids(html, id_pattern)
            new_ids = [i for i in ids if i not in seen]
            seen.update(new_ids)
            all_ids.extend(new_ids)
            print(f"   → {len(new_ids)} new IDs (total: {len(all_ids)})")

            if not new_ids and page > start_page:
                print("   → No new IDs, stopping pagination")
                break

        except Exception as e:
            print(f"   ❌ Error: {e}")

        if page < end_page:
            time.sleep(delay)

    return all_ids


def crawl_detail(config: dict, item_id: str) -> dict:
    """詳細ページを取得してパース"""
    base_url = config.get("base_url", "")
    detail_url = config["detail_url"].replace("{id}", item_id)
    url = f"{base_url}{detail_url}"

    html = fetch_html(url)

    # メタ情報抽出
    meta_patterns = config.get("meta_patterns", {})
    meta = parse_meta(html, meta_patterns)

    # dt/ddパース
    data = parse_dt_dd(html)

    # メタ情報をマージ
    data.update(meta)

    # 元IDを追加
    data[config.get("id_field", "original_id")] = item_id

    return data


def crawl_and_normalize(config: dict, item_id: str) -> dict:
    """詳細を取得して統一スキーマに変換"""
    raw = crawl_detail(config, item_id)
    mapping = config.get("mapping", {})
    return normalize(raw, mapping)


def run(config_path: str, max_pages: int = None, max_items: int = None,
        output_path: str = None, delay: float = None):
    """メイン実行"""
    config = load_site_config(config_path)
    site_name = config.get("name", "unknown")

    if delay is not None:
        config["delay"] = delay

    print(f"🕷️ Crawling: {site_name}")
    print(f"   Base: {config.get('base_url', '')}")

    # Phase 1: ID収集
    print(f"\n📋 Phase 1: Collecting IDs...")
    ids = crawl_list_pages(config, max_pages=max_pages)
    print(f"\n✅ Collected {len(ids)} unique IDs")

    if max_items:
        ids = ids[:max_items]
        print(f"   (limited to {max_items} items)")

    # Phase 2: 詳細取得 + 正規化
    print(f"\n📝 Phase 2: Fetching details...")
    results = []
    crawl_delay = config.get("delay", 1.0)

    for i, item_id in enumerate(ids, 1):
        print(f"   [{i}/{len(ids)}] ID: {item_id}", end=" ")
        try:
            record = crawl_and_normalize(config, item_id)
            record["_crawled_at"] = datetime.utcnow().isoformat()
            record["_source"] = site_name
            results.append(record)
            print("✅")
        except Exception as e:
            print(f"❌ {e}")

        if i < len(ids):
            time.sleep(crawl_delay)

    # Phase 3: 保存
    if not output_path:
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(output_dir / f"{site_name}_{timestamp}.jsonl")

    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n🎉 Done! {len(results)} records saved to {output_path}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HTTP Engine Crawler")
    parser.add_argument("config", help="サイト設定YAMLのパス")
    parser.add_argument("--max-pages", type=int, default=None, help="最大ページ数")
    parser.add_argument("--max-items", type=int, default=None, help="最大取得件数")
    parser.add_argument("--output", "-o", default=None, help="出力ファイルパス")
    parser.add_argument("--delay", type=float, default=None, help="リクエスト間隔（秒）")
    args = parser.parse_args()

    run(args.config, max_pages=args.max_pages, max_items=args.max_items,
        output_path=args.output, delay=args.delay)
