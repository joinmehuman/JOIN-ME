# JOIN ME 静的公開面セキュリティ試験報告

- 試験日：2026年8月25日
- 対象：GitHub Pagesの開発確認ページ、日本危機支援レジストリ、公開停止設定

## 判定

- 現在実装されている静的公開面：PASS（31／31）
- 製品公開Gate：`BLOCKED_NOT_IMPLEMENTED`
- 日本市場：`enabled=false`
- 決済：`payment_enabled=false`

この報告の合格は、入力、AI、認証、暗号化保存、削除、決済の合格を意味しない。

## 今回の整理

1. 7月版の説明ページを、機能の公開状況が正確に分かる開発確認ページへ置換。
2. 実際には開始しないCTA、未提供の料金表示、稼働中と誤解されるAI説明を削除。
3. 古い汎用アニメーションを、モバイルメニューに必要な最小JavaScriptへ置換。
4. HTMLと一致しないCSS、使用していないCSS、版番号表記を削除。
5. Vercel専用の`vercel.json`を削除。
6. GitHub Pages向けにCSP meta、referrer制御、外部自動読込み禁止を検査。

## GitHub Pages上の制限

`Content-Security-Policy`のmeta設定は静的ページで使用できる範囲に限定される。HSTS、`frame-ancestors`など、HTTPレスポンスヘッダーでのみ十分に制御できる項目は本構成の合格対象に含めない。

## 未実装のため試験不能

- 問い・回答の入力と削除E2E
- AI入力前・出力後の二重安全判定
- 認証・認可
- 暗号化したIndexedDB保存
- 期間パス、決済、権利付与
- 本番相当環境へのDASTと第三者侵入試験

## 再現

```sh
python3 tests/security_static.py
```

合格条件：終了コード0、全試験PASS、危機支援情報が期限内、秘密情報0、Vercel専用設定0。

実行結果：終了コード0、31試験すべてPASS。
