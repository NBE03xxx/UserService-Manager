# 新しいチャットへの引き継ぎプロンプト

以下を新しいチャットの最初のメッセージとして使用してください。

---

`/home/yoshimi/WorkSpace/UserService-Manager` の開発を引き継いでください。

## 現在の状態

- プロジェクト: User Service Manager
- ブランチ: `main`
- リモート: `origin`（`github.com:NBE03xxx/UserService-Manager.git`）
- v0.3の機能範囲は実装・検証済みで、ソース版は `v1.3.0` です。
- 本タスクではv1.3.0実装をコミットして`origin/main`へpush済みの状態を引き継ぎます。
- GitHub Releaseとして公開済みの直近版は `v1.2.0` です。v1.3.0のtag・GitHub Releaseは、ユーザーから別途明示指示があるまで作成しないでください。
- `v1.1.0` は版番号を誤って使用したため意図的な欠番です。今後もtag・配布版に再利用しないでください。

## v1.3.0で完了した内容

- 複数drop-inの一覧、作成、編集、削除
- drop-in名、UTF-8、サイズ、構造、所有者、permission、symlinkの検査
- 隔離配置したserviceとdrop-inの`systemd-analyze`検証
- service本体とdrop-inの保存前unified diffと検証結果表示
- drop-inの原子的保存と外部変更競合拒否
- inactive/failedかつ非enabledな直接配置serviceの削除
- service本体、drop-in一式、manifestの非公開・耐久化バックアップ
- 最新バックアップからの非上書き復元
- 変更後のuser manager reloadと再スキャン
- 日本語・英語のdrop-in管理・確認UI

## 検証済み事項

- 自動テスト78件成功
- GSettings、desktop entry、AppStream pedantic検証成功
- Meson configure/build/test/install smoke test成功
- Debian package build成功
- Ubuntu 26.04 LTS / GNOME / Wayland / systemd 259で製品packageを受入
- drop-in作成・編集・検証・差分・バックアップ付き削除・復元を通し確認
- 製品GUIのメイン画面、drop-in一覧、エディター、差分確認を目視確認
- package: `user-service-manager_1.3.0_all.deb`（531776 bytes）
- SHA-256: `9b9db6d023937ac50798f8f4508b1127fd1fc46ef43c2f3af9ef5ea1a1299937`

詳細な証跡は次を確認してください。

- `docs/V0_3_RESULTS.md`
- `docs/RELEASE_READINESS.md`
- `docs/ROADMAP.md`
- `docs/REQUIREMENTS.md`
- `docs/TEST_PLAN.md`
- `docs/SECURITY.md`
- `docs/DECISIONS.md`

## 次に進める段階

次のロードマップ段階は v0.4「systemdユニット拡張」です。

- `.timer`、`.socket`、`.path`の発見・状態・操作
- 関連ユニットの関係表示
- ユニット種別ごとの操作能力と状態表示

着手時は、まず作業ツリー、`main`と`origin/main`、tag・Releaseの状態、CI結果を読み取り専用で確認してください。完了済みのv0.3実装はやり直さず、既存の安全境界を維持してください。

v0.4の要件・設計・脅威モデル・テスト計画を先に整合させ、ユーザーから実装開始の指示があるまではtag追加、GitHub Release公開などの外部変更を行わないでください。

---
