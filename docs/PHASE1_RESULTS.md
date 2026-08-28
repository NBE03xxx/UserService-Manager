# フェーズ1 実装結果

完了日: 2026-08-26  
範囲: プロジェクト基盤。実systemd backendは未実装・未接続。

## 実装したもの

- Python src layoutとMeson build定義
- domain/application/ports/adapters/infrastructure/presentationの依存境界
- UnitId、UnitRecord、state、access mode、registration、capability
- 非同期ServiceBackend protocol
- deterministic mock backend
- ServiceCatalog use case
- system/light/darkと言語設定モデル
- GSettings schema version、登録unit、trusted roots
- GTK 4/libadwaitaの最小一覧画面
- 「午後の喫茶店」のlight/dark visual tokens
- gettext対象文字列と日本語PO
- desktop entry、AppStream metadata
- unittestとCI定義

## 検証

- 通常Wayland sessionで起動
- mockサービス3件を表示
- read-only badgeを表示
- system/light/dark切替
- ライト配色を初回レビュー後、白主体からアイボリー・ミルク・淡い木材色へ修正
- 修正後、利用者が「いい感じ」と確認
- レイアウト・文字崩れなし
- UIソースにsystemd/journal CLI/API参照なし

## 残る制約

- Meson/gettext/pkg-config等は環境へ未導入のため、Meson buildとMO生成は未実行
- AppStream homepageは公開先未決のため未設定
- CI定義は作成済みだがリモートCIでは未実行
- 日本語catalogはPO作成・対応検査まで。MO buildと日本語locale表示はtoolchain導入後に確認
- mock操作ボタンはまだUIへ接続せず、一覧shellの検証に限定
- 実systemd adapter、発見、登録、journal UIは後続フェーズ

## 判定

**Pass with documented toolchain limitations.**

フェーズ2の発見・登録・永続化実装へ進行可能。toolchain package導入は、その作業に必要となる時点で利用者へ確認する。
