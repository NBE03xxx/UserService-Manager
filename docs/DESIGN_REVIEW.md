# v0.1 設計レビュー

## 1. 結論

文書間の基本方針、v0.1 の境界、要件 ID とテストの追跡性は良好である。2026-08-25 に要件所有者がDR-001〜DR-003およびUbuntu方針を決定し、技術スパイクでDR-004とDR-006を解決した。2026-08-26にUbuntu 26.04通常セッションでD-Bus、journal、GSettings、外観、runtime信頼判定、後片付けまで実機検証し、主要ゲートを完了した。

このレビューではコード実装を承認せず、技術スパイクと設計判断の確定を最初のゲートとする。

## 2. 良好な点

- 発見、明示登録、操作認可が別概念として整理されている
- 不明な状態を表示のみに倒す安全側の原則が一貫している
- UI から systemd/journal 接続を分離し、将来の unit 種別追加に備えている
- root、sudo、Polkit を使用しない境界が明確である
- v0.1 と編集・作成・削除機能の境界が明確である
- 37件の要件 ID がテスト計画から追跡可能である
- 日本語・英語対応を初期設計に含めている

## 3. 実装前の重要指摘

### DR-001 — 外部プログラム参照の扱い（解決済み）

`ARCHITECTURE.md` は、解析可能な参照先の一つでもホーム外なら read-only としている。この規則をそのまま適用すると、次のような一般的な定義も表示のみになる。

```ini
ExecStart=/usr/bin/python3 /home/alice/myapp/app.py
```

`/usr/bin/python3` はユーザーが編集する対象ではないが、正規のシステム提供ランタイムである。同様に `/usr/bin/bash`、`/usr/bin/env`、`/usr/bin/node` なども該当する。

実装前に参照先を少なくとも次の役割へ分類する必要がある。

- unit definition: ユニットファイル実体
- system executable/runtime: OS が提供する実行基盤
- user workload: スクリプト、実行ファイル、作業ディレクトリ
- configuration/data: EnvironmentFile 等
- unresolved/dynamic: 指定子や環境展開で静的確定できないもの

**決定:** 信頼できるシステム実行基盤はホーム外でも直ちに read-only の理由とせず、ユーザーが管理する workload/configuration の所在を主な判定対象とする。ADR-007、FR-012 および TC-PATH-005/006 に反映した。

この判断に応じて FR-012〜FR-014、SECURITY、PathPolicy、TC-PATH 系を更新する。

### DR-002 — 「systemd に認識される」の判定（解決済み）

FR-002 は中途半端なファイルを除外するが、「認識」の操作的定義がない。systemd の検索パス上にある、unit として列挙可能、ロード可能、構文エラーがない、のどこまでを要求するかで候補集合が変わる。

**決定:** 読込エラーは黙って除外せず、理由付き表示専用候補とする。ADR-008、FR-002、TC-DISC-001 に反映した。具体的な user manager 問い合わせ方法は技術スパイクで確定する。

### DR-003 — 登録済みサービス消失時の記録（解決済み）

FR-004 は即座に管理対象から除外するとしている。誤操作や一時的な daemon 状態で登録情報まで削除すると、再出現時に登録し直す必要がある。

**決定:** 永続情報を `missing` として保持し、再出現時に自動復元する。明示解除時のみ削除する。ADR-009、FR-004、TC-DISC-002/004 に反映した。

### DR-004 — daemon-reload の認可表現（解決済み）

SEC-005 は表示のみサービスへの `daemon-reload` の個別操作を禁止すると読める一方、設計上の daemon-reload は user manager 全体の操作である。

**決定:** daemon-reload は個別 unit のaccess modeと切り離し、現在ユーザーのuser managerに限定した確認必須の全体操作とする。ADR-017とSEC-005に反映した。

### DR-005 — enable 状態モデル（重要度: Medium）

systemd の enable 状態は enabled/disabled の二値ではない。static、indirect、generated、transient、masked 等を UI と capability にどう写像するかが未決である。

**推奨判断:** 生の状態を保持し、表示ラベルと「enable/disable 可能」の capability を別に算出する。未知の状態を disabled とみなさない。

### DR-006 — 技術スタックと配布境界（解決済み）

GTK のバージョン、実装言語、Ubuntu の最低対応版、パッケージ形式が未決である。これは非同期処理、D-Bus、gettext、テスト方法へ影響する。

**決定:** GTK 4 + libadwaita、Python/PyGObject、Meson、native debを採用する。Ubuntu 26.04を第一受入環境とする。ADR-013〜016とTECHNICAL_SPIKE.mdに記録した。

## 4. テスト計画への指摘

- TC-PATH-001/002 にインタプリタ型 ExecStart とネイティブ実行ファイル型を追加する
- masked/static/indirect/unknown の enable 状態試験を追加する
- user manager が未起動、unit が load-error、daemon-reload 前後の候補状態を追加する
- `missing` を導入する場合、消失・再出現・明示削除を分けて試験する
- 応答性の数値目標（例: 操作中もイベント処理が継続すること）とタイムアウト値は技術スパイク後に決める
- 「対象環境受入試験」に固有 ID を付け、全ての追跡先をテストケース ID に統一する

## 5. レビュー判定

**承認。製品実装の基盤フェーズへ着手可能。**

次を実機で確認済みである。

1. Ubuntu 26.04通常セッションでuser manager D-Bus状態・変更操作
2. journalのuser unit限定条件とcursorページング
3. system runtime信頼判定、load-error、missing、masked、alias
4. GSettingsとsystem/light/dark外観切替
5. 検証用unitとsymlinkの完全な後片付け
6. 39要件の一意性とTEST_PLANからの追跡

`VALIDATION_RESULTS.md` の非ブロッキング項目は、各機能の実装完了条件として継続する。

## 6. 未変更方針

編集、作成、削除、drop-in 管理は引き続き v0.1 対象外とする。レビュー中も実装コードは作成しない。
