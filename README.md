# JOIN ME／問いの鏡

自分を決めつけず、いまの状態と言葉を見つめるための自己観察プロダクトです。

## 現在の公開範囲

このリポジトリのGitHub Pagesは、公開前の開発確認ページです。

- コンセプトと体験予定の流れ
- 選択だけで進む無料の1分体験
- 水庭の波紋、蓮、操作後だけ鳴る生成音
- 常時使える動き・音の停止操作
- 18歳以上向けであること
- 非医療・非診断の安全表示
- 日本の緊急・危機支援先

自由記述入力、AI生成、会員登録、端末保存、決済は公開していません。1分体験の選択内容はメモリ内だけにあり、ページを閉じると消えます。

公開ページ：

- https://joinmehuman.github.io/JOIN-ME/
- https://joinmehuman.github.io/JOIN-ME/trial/
- https://joinmehuman.github.io/JOIN-ME/support-jp.html

## データ方針

- 問い・回答を取得しない
- analytics、session replay、外部送信を使用しない
- localStorage、sessionStorage、IndexedDBへ保存しない
- 外部フォントや第三者スクリプトを自動読込みしない
- 音源ファイルを置かず、利用者が音をオンにした操作後だけWeb Audioで小さな音を生成する

将来入力機能を追加する場合も、問い・回答本文をURL、ログ、分析、Cache Storageへ含めません。

## 主なファイル

- `index.html`：開発確認ページ
- `trial/`：Instagramのプロフィールリンクから直接開ける無料1分体験
- `support-jp.html`：日本の緊急・危機支援先
- `style.css`：両ページ共通の表示
- `script.js`：モバイルメニューのみ
- `config/`：市場・危機支援の公開可否設定
- `legal/`：日本公開前の法務確認項目
- `security/`：試験範囲と結果
- `tests/security_static.py`：静的公開面の回帰試験

## 検証

```sh
python3 tests/security_static.py
```

合格条件は終了コード0、全試験PASS、危機支援情報が確認期限内、秘密情報0件です。

## 公開制御

`config/markets/jp.json`の`enabled=false`および`payment_enabled=false`を維持しています。有資格者の法務承認と製品機能の安全試験が完了するまで、AI入力、会員登録、決済を公開しません。

GitHub Pages版は無料の非商用デモに限定します。オンライン事業、商取引、SaaS、パス販売には使用しません。
