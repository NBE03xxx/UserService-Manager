# v0.1 実装計画

## 1. 前提

この計画は `DESIGN_REVIEW.md` の条件付き承認を前提とする。フェーズ0の判断ゲートを完了するまで製品コードへ着手しない。各作業項目は対応する要件 ID とテストケース ID を持つ。

## 2. フェーズ0 — 技術スパイクと仕様確定

**目的:** 実装方式によって変わる安全境界を先に確定する。

1. 採用済みのGTK 4/libadwaita、Python/PyGObject、Meson、native debの最小環境検証
2. Ubuntu 26.04 LTS を第一検証環境とし、追加で対応する最低 Ubuntu/systemd 範囲を決定
3. user manager の D-Bus API で取得・操作可能な範囲の実機検証
4. python-systemd journal readerと、CLIが必要な診断範囲の検証
5. ExecStart/EnvironmentFile/WorkingDirectory と指定子の解析実験
6. 参照先の役割分類、信頼できる system runtime、unknown の基準決定
7. 発見済み、load-error、missing の状態遷移決定
8. ADR、要件、セキュリティ、テスト計画の更新

**完了ゲート:** `TECHNICAL_SPIKE.md` 第11節の実機検証が完了し、追跡表に漏れがない。

**状態:** 2026-08-26完了。詳細は `VALIDATION_RESULTS.md`。製品実装のフェーズ1へ進行可能。

実機検証の具体的な順序、安全策、後片付け、証跡は `VALIDATION_PLAN.md` に従う。検証結果は `VALIDATION_RESULTS.md` に保存する。

## 3. フェーズ1 — プロジェクト基盤

**対象:** NFR-001、NFR-002、NFR-004、I18N-001〜003、EXT-001〜002

- レイヤー境界と依存方向を持つプロジェクト構成
- formatter、lint、単体テスト、翻訳検査、CI
- backend port と mock adapter
- unit/capability/state/error のドメインモデル
- schema version 付き設定モデル
- gettext カタログと locale 選択
- 意味ベースのデザイントークンと、喫茶店コンセプトの静的UIモックアップ
- system/light/dark の外観設定モデル、システム変更監視、実行中切替

**完了ゲート:** mock backend で英語・日本語の最小画面が応答を保ち、UI が systemd 固有 API を直接参照しない。代表モックアップが UI-005 の視覚レビューを通る。

**状態:** 2026-08-26完了。

- domain/application/ports/adapters/infrastructure/presentationを分離
- backend非依存のUnit/State/Capabilityモデル
- deterministic mock backendとServiceCatalog
- schema version、登録unit、trusted roots、言語、system/light/dark設定
- GTK 4/libadwaita最小画面と喫茶店コンセプトのlight/dark CSS
- gettext sourceと日本語catalog
- Meson、desktop entry、AppStream、CI基盤
- unit、mock操作、設定、翻訳、schema、レイヤー境界の自動テスト
- 通常Wayland sessionでmock 3件、read-only表示、外観切替、文字・レイアウトを目視確認

実systemd D-Bus adapterはフェーズ2以降で実装し、フェーズ1 UIには接続していない。

## 4. フェーズ2 — 発見・登録・永続化

**対象:** FR-001〜005、FR-013〜015、SEC-003、SEC-006

- 発見起点の安全な列挙と canonical unit ID 検証
- systemd user manager との照合
- リンク解決と PathAssessment
- 発見済み未登録候補の取得
- 明示登録、再起動後の復元、再スキャン
- missing/削除の確定済みライフサイクル
- trusted user roots 設定（v0.1に含める場合）

**完了ゲート:** TC-DISC と TC-PATH 系の単体・統合試験が成功し、起点外のファイルが候補へ混入しない。

**状態:** 2026-08-26完了。自動テスト24件と、通常Waylandユーザーセッションでの読み取り統合確認に成功。詳細は `PHASE2_RESULTS.md`。

参照先全体のPathAssessmentはフェーズ3のunit詳細取得と統合済み。操作直前の再検証はフェーズ4で接続する。

## 5. フェーズ3 — 状態照会と一覧 UI

**対象:** FR-006、FR-009、FR-012、FR-016、UI-001〜002、NFR-002〜003

- Description、Active/Sub、enable 生状態、fragment path、ExecStart の取得
- capability と read-only 理由の算出
- 一覧、検索、フィルター、詳細、空・読込・失敗状態
- 表示のみ理由と診断情報コピー
- キーボードとアクセシビリティの基本対応

**完了ゲート:** TC-LIST、TC-INFO、TC-UI-001、TC-ERR-001 が成功し、未知状態を誤って操作可能にしない。

**状態:** 2026-08-26完了。自動テスト33件と、実D-Bus詳細取得、パスポリシー、実サービス一覧、検索・絞り込み、登録永続化をUbuntu 26.04 LTS / GNOME / Waylandで確認。詳細は `PHASE3_RESULTS.md`。

## 6. フェーズ4 — 変更操作

**対象:** FR-007〜010、FR-017、SEC-001〜005、UI-003

- start/stop/restart、enable/disable の adapter
- 操作直前の登録・存在・パス・capability 再検証
- unit 単位の操作直列化、timeout、cancel、完了後再取得
- 確認ダイアログと成功・失敗通知
- user manager 限定 daemon-reload と全体再スキャン
- 注入、TOCTOU、領域外差替え試験

**完了ゲート:** TC-OPS と TC-SEC-001〜003 が成功し、権限昇格を一切要求しない。

**状態:** 2026-08-26完了。自動テスト39件、製品コード経由のstart/stop/restart、enable/disable、user manager reload、操作UI、確認画面を実機確認し、検証unitの復元・削除まで完了。詳細は `PHASE4_RESULTS.md`。

## 7. フェーズ5 — journal 表示

**対象:** FR-011、SEC-007、NFR-002〜003

- canonical unit で限定した journal query
- 件数上限、ページング、更新、キャンセル
- 日時・優先度・メッセージ表示、コピー
- 空状態、journal 不在、権限不足、巨大出力への対応
- 診断と機密値マスキング

**完了ゲート:** TC-LOG-001、TC-SEC-004、TC-ERR-001 が成功し、独自ログ保存がない。

**状態:** 2026-08-27完了。自動テスト46件、実journalのunit/UID限定取得、cursorページング、ログUI、検索、コピー、更新完了表示を確認。詳細は `PHASE5_RESULTS.md`。

## 8. フェーズ6 — 統合・受入・リリース準備

- 全要件追跡表の再生成・レビュー
- Ubuntu/GNOME/Wayland の隔離テストユーザーで受入試験
- 日本語、英語、未対応 locale、疑似翻訳の確認
- システム追従、手動ライト／ダーク、再起動後の永続化、実行中切替の確認
- キーボード操作と支援技術ラベルの確認
- 異常終了後の設定整合性、外部変更、再スキャン試験
- README の既知制約、対象外機能、安全な配置説明の確認
- セキュリティレビューとリリース判定

**完了ゲート:** `TEST_PLAN.md` の v0.1 リリース基準を全て満たす。

**状態:** 実装受入を進行中。要件追跡、自動テスト49件、metadata、日英UI受入は完了。package build、縮退環境、アクセシビリティ実機試験が未完了のため、配布リリースは未承認。詳細は `ACCEPTANCE_CHECKLIST.md` と `RELEASE_READINESS.md`。

## 9. 推奨実装順序と依存関係

```text
仕様確定
  └─ 基盤・ドメイン
       ├─ 発見・登録・PathPolicy
       │    └─ 状態一覧
       │         ├─ 変更操作
       │         └─ journal表示
       └─ i18n・設定（各段階で継続）
                    └─ 統合受入
```

安全性判定を UI より先に実装・試験し、操作 adapter は可操作性判定が完成するまで接続しない。

## 10. 作業単位の完了条件

各作業は、設計更新、実装、単体/統合テスト、該当要件 ID、利用者向け文言、失敗時挙動が揃って完了とする。仕様と挙動が異なる場合はコードに合わせて文書を変えるのではなく、要件判断へ戻す。
