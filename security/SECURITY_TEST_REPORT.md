# JOIN ME 実装セキュリティ試験報告

- 試験日：2026-08-20
- 基準コミット：711d8c865ce803413f6d00c04c024695453c2b20
対象：現行の静的ランディング面、追加した日本危機支援レジストリ、Vercelヘッダー設定

## 判定

- 現在実装されている静的公開面：PASS（24／24）
- Critical／High：検出0件（本対象範囲）
- 問い・回答本文の外部送信：入力面自体が存在しないため0件
- 製品公開Gate：BLOCKED_NOT_IMPLEMENTED

「静的公開面の試験合格」は、未実装のAI・認証・暗号化保存・削除・決済・危機分岐の合格を意味しない。未実装項目をPASS扱いせず、Country GateとPayment Gateを閉じた。

## 合格した試験

1. index／危機支援ページの単一html・body構造、重複IDなし、ローカル参照欠落なし。
2. フォーム・入力欄・contenteditableなし、第三者資産の自動読込みなし。
3. JavaScript構文、動的コード実行・HTML sinkなし、ネットワーク送信APIなし。
4. analytics／session replayなし、既知形式の秘密情報なし。
5. 110円／380円、自動更新なし、月額なしが一致し、旧価格0件。
6. JP Country Profileの価格設定一致、法務未承認時の`enabled=false`／`payment_enabled=false`。
7. CSP、HSTS、nosniff、DENY、Referrer-Policy、Permissions-Policy、COOP設定あり。
8. JP危機レジストリ9ルート、公式機関ドメイン、確認期限、画面との番号一致。
9. CSSの外部資産0件。

## 未実装のため試験不能

- 入力前Risk Classifierと出力後Safetyの二重判定。
- prompt injection、system prompt漏えい、危険出力、resource exhaustion。
- 認証・認可、CSRF、rate limit、credential stuffing。
- AES-GCM／IndexedDB保存、IV一意性、平文0、削除後再取得0。
- Stripe、権限、Webhook、110円／380円の決済E2E。
- 本番相当環境へのDASTと第三者penetration test。
- market／model／payment kill switchの実演。

## 再現

```sh
python3 tests/security_static.py
git diff --no-index --check ../JOIN-ME-baseline .
```

合格条件：試験プロセス終了コード0、24試験すべてPASS、危機レジストリ期限内、旧価格0、秘密情報0。
