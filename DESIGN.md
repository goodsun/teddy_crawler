# Teddy Crawler 設計メモ

## 設計思想
- 求人クロールは最初のユースケース。クローラー自体は汎用基盤
- パターンごとにエンジンを分ける（無理に統一しない）
- サイト定義はYAMLで宣言的に。コードを書かずに横展開できるのが理想

## エンジン分類（2026-02-12調査）

### ① HTTP Engine（SSR）— 大多数
requests/curlで取得可能。Playwright不要。
- キャディカル、kaigo-garden、yakumatch、マイナビ薬剤師、phget、oshigoto-lab、rikunabi-yakuzaishi、mjc-pharmajob、seiyakuonline、kango.firstnavi 等

### ② Playwright Engine（SPA）
JS実行しないとコンテンツが空。
- pharmapremium.jp（content 0%）
- nurse.medrt.com（content 3%）

### ③ API Engine
SPAサイトの裏APIを直叩き。最も効率的だが調査が必要。

## パーサー分類
- **dt/dd パターン**: 最多数派。キャディカル等
- **table パターン**: マイナビ薬剤師等
- **JSON API**: SPA系の裏API
- **custom**: 独自構造のサイト

## ディレクトリ構成（予定）
```
teddy_crawler/
├── crawler.py          # 既存の汎用CLI
├── engines/
│   ├── http_engine.py  # SSR用
│   ├── pw_engine.py    # SPA用（Playwright）
│   └── api_engine.py   # API直叩き
├── parsers/
│   ├── dt_dd.py        # dt/ddパターン
│   ├── table.py        # tableパターン
│   └── json_api.py     # JSONレスポンス
├── core/
│   ├── diff.py         # 差分検出（新着判定）
│   ├── scheduler.py    # 定期巡回
│   └── notify.py       # 通知（Telegram等）
├── projects/           # ユースケース別
│   ├── medical_jobs/   # 医療求人クロール
│   │   ├── config.yaml
│   │   ├── sites/
│   │   │   ├── cadical.yaml
│   │   │   ├── kaigo_garden.yaml
│   │   │   └── ...
│   │   └── state/      # 前回取得状態
│   └── (将来: tech_news/ etc.)
├── extractors/         # 既存
├── storage/            # 既存
└── output/
```

## 対象サイト一覧（33サイト）
→ /tmp/crawl.txt 参照

## キャディカル分析結果（2026-02-12）
- SSR、Playwright不要
- 一覧: /search/?p=1〜90 でページネーション
- ID抽出: `job_id=(\d+)` 正規表現で取得可能
- 詳細: /search/details/?job_id=XXXXX
- パーサー: dt/ddパターンで全フィールドkey-value化OK
- 更新日フィールドあり → 差分検出に利用可能

## 次のステップ
1. engines/http_engine.py を実装（一覧巡回→ID収集→詳細取得の基本フロー）
2. parsers/dt_dd.py を実装
3. キャディカルをサンプルとして動かす
4. 差分検出・通知を追加
5. 他のSSRサイトに横展開
