# v1.3.1 文書方針整合・回帰検証結果

実施日: 2026-09-21
製品版: v1.3.1（v1.1.0は欠番）
第一検証環境: Ubuntu 26.04 LTS / GNOME / Wayland / systemd 259

## 判定

**文書整合性: 合格。v1.3.1文書更新リリース: 承認。**

一般ユーザーのsystemd `.service`管理を現在の製品範囲として維持する。systemdユニット種別の拡張、関連表示、高度ログ、追加Debian系環境の検証は必要性が具体化した場合の将来構想とし、cronバックエンドとアプリ内の手動言語選択は実装計画から除外した。

## 文書監査

- README、要件、テスト計画、ロードマップ、アーキテクチャ、ADR、国際化、引き継ぎ文書を同一方針へ整合
- v0.4という確定した次期段階を廃止し、将来構想に版・期限を割り当てない方針へ変更
- `I18N-003`と`EXT-002`を要件・追跡表から同時に除去
- 能力モデルとport分離は拡張の約束ではなく、安全性とテスト容易性のため維持
- v1.3.0のtag、GitHub Release、成果物、CI成功を公開済み証跡として反映
- 方針の再不整合を防ぐ契約テストを追加

## 自動・パッケージ検証

- 単体・契約テスト79件成功
- 要件IDとTEST_PLAN追跡IDの完全一致
- Python compileall成功
- GSettings schema strict dry-run成功
- desktop entry検証成功
- AppStream offline pedantic検証成功
- Debian package build中のMeson test成功
- package metadata、導入版、Python package版が1.3.1で一致

## Ubuntu 26.04回帰受入

v1.3.1 packageをv1.3.0からupgradeし、製品packageのコードで既存のv1.3 lifecycle acceptanceを再実行した。drop-in作成・編集・systemd検証・差分、バックアップ付きservice削除、非上書き復元、reload、再スキャンが成功した。検証unit、drop-in、バックアップ、user manager読込状態は後片付け済みである。

## 配布成果物

- ファイル: `user-service-manager_1.3.1_all.deb`
- サイズ: 532000 bytes
- SHA-256: `1145d0cfd44aebc94d4c94473e2bf8a1886355dea9732cbb78081274d32e039f`
- GitHub Release: <https://github.com/NBE03xxx/UserService-Manager/releases/tag/v1.3.1>

## 変更境界

アプリの機能コードとv0.3の安全境界は変更していない。変更対象は文書、版情報、AppStream metadata、Debian changelog、方針整合を検査する契約テストだけである。
