# 新しいチャットへの引き継ぎプロンプト

以下を新しいチャットの最初のメッセージとして使用してください。

---

`/home/yoshimi/WorkSpace/UserService-Manager` の開発を引き継いでください。

## 現在の状態

- プロジェクト: User Service Manager
- ブランチ: `main`
- リモート: `origin`（`github.com:NBE03xxx/UserService-Manager.git`）
- v0.2の機能範囲は実装・検証済みで、製品版 `v1.2.0` として公開済みです。
- GitHub Release: <https://github.com/NBE03xxx/UserService-Manager/releases/tag/v1.2.0>
- リリースコミット: `f7a33d24dac459896a35c0336c69d19f7875fc15`（`Release version 1.2.0`）
- 直前の文書整合性修正: `cc9c416`（`Align documentation with v1.0.1 release`）
- `v1.1.0` は版番号を誤って使用したため意図的な欠番です。今後もtag・配布版に再利用しないでください。

## v1.2.0で完了した内容

- GUIからのユーザーserviceファイル新規作成・編集
- UTF-8、サイズ、NUL、directive形式、`[Service]`の保存前検査
- `/usr/bin/systemd-analyze`による保存前検証
- 安全な通常ファイル・所有者・permissionの検査
- SHA-256リビジョンによる外部変更競合の拒否
- mode 0600一時ファイルと`os.replace`による原子的保存
- 利用者が選択した場合だけ作成するタイムスタンプ付きバックアップ
- 保存後のuser manager reloadと再スキャン
- 日本語・英語のエディター、作成・編集ボタン、`Ctrl+N`

## 検証済み事項

- 自動テスト66件成功
- GSettings、desktop entry、AppStream検証成功
- Meson configure/build/test/install smoke test成功
- Debian package build成功
- Ubuntu 26.04 LTS / GNOME / Wayland / systemd 259で実機受入成功
- 作成、検証、原子的編集、バックアップ、reload、再スキャン、競合拒否を通し確認
- GitHub Actions run `35497831169` 成功
- 公開パッケージ: `user-service-manager_1.2.0_all.deb`（524840 bytes）
- SHA-256: `bdbb081ba1bfe9055523508901743d28c42947a91e859dd2bec4ce4ba0cf24fc`

詳細な証跡は次を確認してください。

- `docs/V0_2_RESULTS.md`
- `docs/RELEASE_READINESS.md`
- `docs/ROADMAP.md`
- `docs/REQUIREMENTS.md`
- `docs/TEST_PLAN.md`
- `docs/SECURITY.md`
- `docs/DECISIONS.md`

## 次に進める段階

次のロードマップ段階は v0.3「drop-in とライフサイクル」です。

- `systemctl --user edit`相当の制限を持つoverride作成・編集
- 複数drop-inの閲覧・管理
- serviceの削除と復元可能なバックアップ導線
- 変更差分と検証結果のプレビュー

着手時は、まず現在の作業ツリー、`main`と`origin/main`、tag・Releaseの状態を読み取り専用で確認してください。完了済みのv0.2実装やv1.2.0公開はやり直さず、既存の安全境界を維持してください。

その後、v0.3の要件・設計・脅威モデル・テスト計画にある不足や不整合を調査し、実装前に作業範囲と段階案を提示してください。ユーザーから実装開始の指示があるまでは、リリース作成、tag追加、外部公開などの変更は行わないでください。

---
