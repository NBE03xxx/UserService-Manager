# 新しいチャットへの引き継ぎプロンプト

以下を新しいチャットの最初のメッセージとして使用してください。

---

`/home/yoshimi/WorkSpace/UserService-Manager` の開発を引き継いでください。

## 現在の状態

- プロジェクト: User Service Manager
- ブランチ: `main`
- リモート: `origin`（`github.com:NBE03xxx/UserService-Manager.git`）
- v0.3の機能範囲は実装・検証済みで、v1.3.0として公開済みです。
- v1.3.1は機能コードを変えず、公開状態と今後の対象範囲を整合した文書更新版です。
- 公開Release: <https://github.com/NBE03xxx/UserService-Manager/releases/tag/v1.3.1>
- `v1.1.0` は版番号を誤って使用したため意図的な欠番です。今後もtag・配布版に再利用しないでください。

## v1.3系で完了した内容

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

- 自動テスト79件成功
- GSettings、desktop entry、AppStream pedantic検証成功
- Meson configure/build/test/install smoke test成功
- Debian package build成功
- Ubuntu 26.04 LTS / GNOME / Wayland / systemd 259で製品packageを受入
- drop-in作成・編集・検証・差分・バックアップ付き削除・復元を通し確認
- 製品GUIのメイン画面、drop-in一覧、エディター、差分確認を目視確認
- package: `user-service-manager_1.3.1_all.deb`（532000 bytes）
- SHA-256: `1145d0cfd44aebc94d4c94473e2bf8a1886355dea9732cbb78081274d32e039f`

詳細な証跡は次を確認してください。

- `docs/V0_3_RESULTS.md`
- `docs/V1_3_1_RESULTS.md`
- `docs/RELEASE_READINESS.md`
- `docs/ROADMAP.md`
- `docs/REQUIREMENTS.md`
- `docs/TEST_PLAN.md`
- `docs/SECURITY.md`
- `docs/DECISIONS.md`

## 今後の方針

現在の製品範囲である一般ユーザーのsystemd `.service`管理を維持します。次の項目は版や期限を定めない将来構想です。

- `.timer`、`.socket`、`.path`の発見・表示・操作
- 関連ユニットの関係表示
- ユニット種別ごとの操作能力と状態表示
- システムサービスを含む管理範囲の再検討
- 高度なログフィルター、診断エクスポート
- Ubuntu以外を含むDebian系ディストリビューションでの検証拡大

cronバックエンドとアプリ内の手動言語選択は実装計画に含めません。

将来構想へ着手する場合は、まず作業ツリー、`main`と`origin/main`、tag・Release、CIを読み取り確認し、必要性、要件、脅威モデル、テスト計画を再定義してください。完了済みのv0.3実装や安全境界はやり直さないでください。

---
