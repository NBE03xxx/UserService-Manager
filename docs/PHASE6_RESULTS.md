# フェーズ6 統合・リリース監査結果

## 判定

実装受入は合格とする。主要機能と安全性、ネイティブbuildと配布往復試験、アクセシビリティ、公開homepage URLを確認し、v1.0.0の正式リリース条件を満たした。

## 自動検証

- 2026-08-27にunit test 50件が成功
- Python構文検査が成功
- GSettings schemaのstrict dry-runが成功
- desktop entry検証が成功
- AppStream XMLは解析に成功し、homepage URL未設定のwarningのみが残存
- REQUIREMENTSの39 IDとTEST_PLANの追跡IDの完全一致をtestで確認

## 実機受入で確認した項目

- Ubuntu 26.04 LTS / GNOME / Waylandでの主要機能
- 日本語・英語表示とレイアウト
- light、dark、通常セッションでのsystem動的追従
- user bus利用不能時のread-only縮退、再試行、診断コピー
- journal利用不能時のエラー表示と復帰
- journalの更新、ページング、検索、コピー
- キーボードのみでの主要操作、`Esc`によるログ画面の終了、2倍表示でのレイアウトとスクロール

## フェーズ6で修正した主要事項

- エラー要約と診断詳細を分離し、診断情報は明示的なコピーでのみ取得するようにした
- system外観のAdwaita設定を修正し、通常セッションでGNOMEの変更に追従させた
- ログ画面で`Esc`を受け取るkey controllerを追加した
- gettext catalog、要件追跡、外観設定の自動testを追加した
- Debian packagingの初期定義とCIのbuild手順を追加した
- 配布ランチャーの既定値を実systemd backendと安全ゲート付き変更操作にし、検証用mockを製品起動しないことを自動testで固定した
- Meson configure/build/test、gettext catalog build、一時領域へのinstall smoke testが成功した
- `user-service-manager_0.1.0~dev1_all.deb`のbuildと内容・依存関係の静的検査が成功した
- Ubuntu 26.04 LTSで`.deb`を実インストールし、実際のuser service、日本語、外観、登録状態を使う製品モードの起動に成功した
- `.deb`のuninstall/reinstallに成功し、再インストール後も登録サービスと外観設定が保持された
- Open JTalk日本語音声を使うOrcaで主要button、サービス状態、read-only理由、確認画面の読み上げが理解可能であることを確認した

## 残作業

なし。

## 既知の制約

user busを意図的に利用不能にした縮退状態では、GNOMEの外観設定と変更通知も取得できない。この場合の`system`追従は保証しないが、手動のlight/darkと安全なread-only表示は利用できる。

FR-015の追加管理範囲UIはShould要件として後続フェーズへ送る。v0.1では既定の安全なユーザー領域だけを管理可能判定に使う。

## 最終ビジュアル

トップは「ユーザーサービスマネージャー」、副題は「〜ごゆっくりどうぞ〜」とする。ヒーロー画像は、透明背景の受け皿付きコーヒーカップを茶系単色に近い線画で表し、96px相当で表示する。ライト・ダークの両方で実画面を確認済みとする。
