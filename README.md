# Teddy Crawler 🐻

Playwrightベースの汎用Webクローラー基盤

## 概要

Teddy Crawlerは、JavaScript動的サイトに対応したWebクローラーです。URLを指定するだけで、テキスト・画像・リンクを自動収集し、JSON形式で保存します。

## 特徴

- 🎭 **Playwright powered**: JavaScript動的サイト完全対応
- ⚙️  **設定ファイル駆動**: YAML設定で柔軟なクロール定義
- 🖥️  **CLI対応**: コマンドラインから手軽に操作
- 📋 **汎用抽出**: テキスト・リンク・画像を自動抽出
- 🎯 **セレクタ対応**: CSS/XPathセレクタで特定要素を取得
- ⏳ **レート制限**: サーバー負荷を考慮した間隔制御
- 📸 **スクリーンショット**: ページの見た目も保存可能
- 🍪 **Cookie/Profile対応**: ログイン状態を維持
- 📊 **統計レポート**: クロール結果をサマリー出力

## インストール・セットアップ

### 前提条件

- Python 3.9+
- Playwright（既にインストール済み）
- PyYAML（既にインストール済み）

### Playwrightブラウザのインストール

```bash
# Chromiumブラウザをインストール
python3 -m playwright install chromium
```

## 基本的な使い方

### 1. 単一URL取得

```bash
# 基本的な取得
python3 crawler.py fetch https://example.com

# オプション付きで取得
python3 crawler.py fetch https://example.com --screenshot --wait 5000 --scroll
```

### 2. バッチ処理

```bash
# 設定ファイルを使用したバッチクロール
python3 crawler.py batch config.yaml

# カスタム設定ファイル
python3 crawler.py batch my_custom_config.yaml --output my_results.json
```

### 3. 出力ファイル確認

```bash
# 出力ファイル一覧表示
python3 crawler.py list
```

## 設定ファイル（config.yaml）

### 基本構成

```yaml
# グローバル設定
settings:
  delay: 2000                           # リクエスト間隔（ミリ秒）
  timeout: 30000                        # タイムアウト（ミリ秒）
  user_agent: "TeddyCrawler/1.0"        # User-Agent
  screenshot: false                     # スクリーンショット取得
  profile: null                         # プロファイル名
  output_format: "json"                 # 出力形式

# クロールジョブ定義
jobs:
  - name: "example_job"
    url: "https://example.com"
    extract: ["text", "links", "images"]
    wait: 2000
    scroll: false
    screenshot: false
```

### サンプル設定

#### note.com トレンド記事

```yaml
jobs:
  - name: "note_trending"
    url: "https://note.com/search?q=AI&sort=trend"
    selectors:
      title: "h3 a"
      link: "a[href*='/n/']"
      author: ".note-common-authors a"
    wait: 3000
    scroll: true
    scroll_count: 3
    extract: ["text", "links"]
```

#### GitHub リポジトリ情報

```yaml
jobs:
  - name: "github_repo"
    url: "https://github.com/microsoft/playwright"
    selectors:
      repo_name: "h1[data-view-component=true] strong a"
      description: "p[data-view-component=true]"
      stars: "#repo-stars-counter-star"
      language: "[data-view-component=true][data-testid*=language]"
    extract: ["text", "links"]
    wait: 2000
```

## コマンドラインオプション

### fetchコマンド

```bash
python3 crawler.py fetch <URL> [オプション]

オプション:
  -o, --output FILENAME     出力ファイル名
  -s, --screenshot          スクリーンショットを取得
  -p, --profile PROFILE     プロファイル名を指定
  -ua, --user-agent AGENT   User-Agent文字列
  -w, --wait MILLISECONDS   待機時間（ミリ秒）
  --scroll                  無限スクロール対応
  --headful                 ブラウザを表示（デバッグ用）
```

### batchコマンド

```bash
python3 crawler.py batch <CONFIG_FILE> [オプション]

オプション:
  -o, --output FILENAME     出力ファイル名
```

## 抽出可能なデータ

### テキスト（text）

- ページタイトル
- メイン記事コンテンツ
- 段落テキスト
- 見出し（h1-h6）
- メタディスクリプション

### リンク（links）

- 内部リンク・外部リンク
- ナビゲーションリンク・コンテンツリンク
- 画像付きリンク
- リンクテキスト・タイトル

### 画像（images）

- img要素の画像
- CSS背景画像
- alt属性・title属性
- 画像サイズ・形式別統計

## プロファイル機能

### 既存のteddy_browserプロファイル利用

```yaml
settings:
  profile: "default"  # /home/ec2-user/tools/teddy_browser/profiles/default を使用
```

### ローカルプロファイル作成

```bash
# プロファイル用ディレクトリ
mkdir -p profiles/my_profile
```

```yaml
settings:
  profile: "my_profile"  # ./profiles/my_profile を使用
```

## 出力形式

### JSON形式（デフォルト）

```json
{
  "metadata": {
    "crawled_at": "2024-01-15T10:30:00Z",
    "url": "https://example.com",
    "crawler_version": "1.0.0"
  },
  "data": {
    "text": {
      "title": "Example Page",
      "content": "Main content text...",
      "paragraphs": ["段落1", "段落2"]
    },
    "links": {
      "internal_links": [...],
      "external_links": [...],
      "total_count": 25
    },
    "images": {
      "images": [...],
      "total_count": 8
    }
  }
}
```

### JSONL形式

```yaml
settings:
  output_format: "jsonl"
```

各行が1つのJSONオブジェクトとして保存されます。

## 実用例

### 1. ニュースサイトのヘッドライン収集

```bash
python3 crawler.py fetch https://www3.nhk.or.jp/news/ \
  --screenshot --wait 3000 --output nhk_news.json
```

### 2. ECサイトの商品情報取得

```yaml
jobs:
  - name: "product_info"
    url: "https://example-shop.com/products/123"
    selectors:
      title: "h1.product-title"
      price: ".price"
      description: ".product-description"
      images: ".product-images img"
    wait: 2000
    extract: ["text", "images"]
```

### 3. ソーシャルメディア投稿収集

```yaml
jobs:
  - name: "social_posts"
    url: "https://example-social.com/hashtag/AI"
    scroll: true
    scroll_count: 5
    wait: 4000
    selectors:
      posts: ".post-content"
      authors: ".post-author"
      timestamps: ".post-time"
```

## トラブルシューティング

### よくあるエラー

#### 1. タイムアウトエラー

```yaml
settings:
  timeout: 60000  # タイムアウト時間を延長
```

#### 2. 要素が見つからない

```yaml
jobs:
  - name: "example"
    url: "https://example.com"
    wait: 5000      # 待機時間を延長
    scroll: true    # スクロールして要素を読み込み
```

#### 3. ブラウザ起動エラー

```bash
# Playwrightブラウザを再インストール
python3 -m playwright install chromium
```

### デバッグモード

```bash
# ブラウザを表示してデバッグ
python3 crawler.py fetch https://example.com --headful
```

```yaml
debug:
  verbose: true
  headful: true
  devtools: true
```

## ディレクトリ構成

```
teddy_crawler/
├── README.md              # このファイル
├── crawler.py             # メインクローラーエンジン
├── config.yaml            # サンプル設定ファイル
├── extractors/            # データ抽出モジュール
│   ├── __init__.py
│   ├── text.py            # テキスト抽出
│   ├── links.py           # リンク抽出
│   └── images.py          # 画像抽出
├── storage/               # データ保存モジュール
│   ├── __init__.py
│   └── json_store.py      # JSON保存
├── profiles/              # ローカルプロファイル
└── output/                # クロール結果出力先
    ├── crawl_20240115_103000_example.json
    ├── batch_crawl_20240115_103500.json
    └── summary_report_20240115_104000.json
```

## 貢献・開発

### 機能拡張

新しい抽出機能を追加する場合は、`extractors/`ディレクトリに新しいモジュールを作成してください。

### カスタムストレージ

JSON以外の保存形式が必要な場合は、`storage/`ディレクトリにカスタムストレージクラスを追加してください。

## ライセンス・注意事項

### 利用時の注意

1. **robots.txt を確認**: サイトのクロール可否を事前確認
2. **レート制限を設定**: サーバー負荷を避ける
3. **利用規約を遵守**: 各サイトの利用規約に従う
4. **著作権に注意**: 収集データの利用方法に注意

### 推奨設定

```yaml
settings:
  delay: 2000    # 最低2秒間隔
  timeout: 30000 # 適切なタイムアウト設定
  user_agent: "Your-Bot-Name/1.0 (contact@example.com)"  # 連絡先を含む
```

---

Happy Crawling! 🐻🕸️