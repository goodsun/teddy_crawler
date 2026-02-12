# 初回設計議論 — 2026-02-12

## 背景
マスターの仕事関連で、医療・介護・薬剤師系の求人サイト（33サイト）から新着求人を定期取得したい。ただしクローラー自体は汎用基盤として設計し、求人以外のユースケースにも対応できるようにする。

## キャディカル（iryoushoku.cadical.jp）での実地調査

### サイト構造
- **一覧ページ**: `https://iryoushoku.cadical.jp/search/?p={page}` （全90ページ）
- **詳細ページ**: `https://iryoushoku.cadical.jp/search/details/?job_id={id}`
- **ページネーション**: `?p=1`〜`?p=90`、HTMLにリンクあり
- **ID抽出**: HTMLに `job_id=(\d+)` がリンクとして埋まっている

### 詳細ページの構造
```html
<dt>勤務先</dt>
<dd>千種さわやかクリニック</dd>
<dt>勤務地</dt>
<dd>愛知県名古屋市</dd>
<dt>給与</dt>
<dd>基本給：300,000円/月...</dd>
```
→ `<dt>/<dd>` ペアを正規表現で抽出するだけで全フィールドがkey-value化できる。

### 取得テスト結果（job_id=44928）
```json
{
  "job_id": "44928",
  "title": "【名古屋市】高収入！18時まで！訪問診療クリニックのエリアマネージャー候補求人",
  "update_date": "2026/02/12",
  "勤務先": "千種さわやかクリニック",
  "勤務地": "愛知県名古屋市",
  "最寄駅": "千種(ＪＲ中央本線(名古屋－塩尻)), 千種(名古屋市営地下鉄東山線)",
  "アクセス": "JR千種駅から徒歩5分",
  "給与": "基本給：300,000円/月\n賞与：約900,000円/年",
  "職種": "その他",
  "雇用形態": "正社員",
  "業種": "クリニック",
  "仕事内容": "...",
  "応募条件": "...",
  "勤務時間": "09:00～18:00　(休憩1時間)",
  "休日休暇": "年間休日124日...",
  "保険": "有（健康保険、厚生年金、労災保険、雇用保険）",
  "福利厚生": "...",
  "受動喫煙対策": "敷地内禁煙",
  "特徴": "...",
  "企業情報": "..."
}
```

## 33サイト一括調査結果

### 技術パターン分類

| パターン | 説明 | 該当数 | 例 |
|---------|------|--------|-----|
| SSR + dt/dd | サーバーサイドレンダリング、dt/ddで構造化 | 大多数 | キャディカル、kaigo-garden、yakumatch、phget、mjc-pharmajob |
| SSR + table | テーブル構造 | 一部 | マイナビ薬剤師、cocofump-job |
| SPA | JSレンダリング必須、curlではコンテンツ空 | 2-3 | pharmapremium.jp (0%), nurse.medrt.com (3%) |

### 調査データ
```
kaigo-garden.jp:       114KB | SSR | dt/dd=True
phama.selva-i.co.jp:   463KB | SSR | dt/dd=True
yakuzaishi.yakumatch:   58KB | SSR | dt/dd=True
pharma.mynavi.jp:      411KB | SSR | dt/dd=True, table=True
cocofump-job.net:       79KB | SSR | dt/dd=True, table=True
yakusta.com:           163KB | SSR | dt/dd=True
phget.com:              56KB | SSR | dt/dd=True | content=44%
oshigoto-lab.com:       73KB | SSR | dt/dd=False | content=31%
rikunabi-yakuzaishi:    51KB | SSR | dt/dd=True | content=27%
pharmapremium.jp:      271KB | SPA | content=0% ← Playwright必須
mjc-pharmajob.com:      85KB | SSR | dt/dd=True | content=20%
nurse.medrt.com:       314KB | SPA | content=3% ← Playwright必須
seiyakuonline.com:     162KB | SSR | dt/dd=True | content=28%
kango.firstnavi.jp:     45KB | SSR(React) | dt/dd=True | content=31%
```

## 設計方針（合意事項）

### パターンごとにエンジンを分ける
無理に1つのシステムで統一しない。

- **HTTP Engine**: SSRサイト用。requests/curlベース。大多数をカバー
- **Playwright Engine**: SPAサイト用。JSレンダリング必須な少数派向け
- **API Engine**: SPAサイトの裏APIを直接叩く。最効率だが調査コストあり

### 汎用基盤 + ユースケース別プロジェクト
```
teddy_crawler/
├── engines/        # 汎用エンジン
├── parsers/        # 汎用パーサー
├── core/           # 差分検出、通知
└── projects/       # ユースケース別
    ├── medical_jobs/   # 今回のメイン
    └── ...             # 将来拡張
```

### クローラーの汎用的なユースケース
- 求人サイト新着監視（今回）
- 競合サイト監視（価格変動、新サービス）
- ニュース・技術記事の自動収集
- SNSトレンド把握
- 行政サイト更新検知（補助金、入札情報）
- ECサイト在庫・価格追跡

## クロール戦略（SSRサイト共通パターン）
1. **一覧ページ巡回** → ページネーションを辿ってID一覧を取得
2. **差分検出** → 前回取得IDと比較、新着のみ抽出
3. **詳細ページ取得** → 新着IDの詳細をクロール、key-value化
4. **保存** → JSONL形式で蓄積
5. **通知** → 新着があればTelegram等で通知

## 次のステップ
1. engines/http_engine.py（一覧巡回→ID収集→詳細取得）
2. parsers/dt_dd.py（dt/ddパターンの汎用パーサー）
3. キャディカルで動作確認
4. core/diff.py（差分検出）
5. 他SSRサイトへ横展開
6. Playwright Engine は必要になってから
