# v1.3.0 リリース準備状況

## 判定

**実装受入: 合格。コミット・push: 承認。**

v1.2.0までの閲覧・操作・journal・作成・編集に加え、v0.3のdrop-inとライフサイクルをUbuntu 26.04 LTSで受入した。実装・コミットを阻害する未完了項目はない。

## v1.3.0で追加した機能

- 複数`.conf` drop-inの一覧、作成、編集、削除
- drop-inの構造検査とsystemd自身による隔離配置検証
- service・drop-in変更前のunified diffと検証結果表示
- 停止・無効化済みserviceのバックアップ付き削除
- service本体とdrop-in一式の最新バックアップ復元
- 削除・復元の外部競合拒否、非上書き保存、reload・再スキャン
- 日本語・英語のdrop-in管理、エディター、確認画面

## 完了した証跡

- 要件IDとTEST_PLAN追跡IDが完全一致
- 自動テスト78件成功
- GSettings、desktop entry、AppStream検証成功
- Meson configure/build/test/install smoke test成功
- Debian package buildとbuild内test成功
- Ubuntu 26.04 LTS VMへの1.3.0 package upgrade成功
- 製品コードでdrop-in作成・編集・検証・差分・削除バックアップ・復元を通し確認
- 製品モードのメイン画面、drop-in一覧・エディター・差分確認をGNOME/Wayland上で目視確認
- 検証unit、drop-in、バックアップ、user manager読込状態の後片付け完了

詳細は`V0_3_RESULTS.md`を参照する。v1.2.0までの証跡は`V0_2_RESULTS.md`、`PHASE1_RESULTS.md`〜`PHASE6_RESULTS.md`、`ACCEPTANCE_CHECKLIST.md`に保持している。

## 配布候補

- version: `1.3.0`
- package: `user-service-manager_1.3.0_all.deb`
- package size: 531776 bytes
- SHA-256: `9b9db6d023937ac50798f8f4508b1127fd1fc46ef43c2f3af9ef5ea1a1299937`
- v1.1.0は誤用のため欠番とし、tag・配布版に再利用しない

本タスクではコミットと`main`へのpushまでを行う。tag作成とGitHub Release公開は別途明示指示がある場合に実施する。

## 既知の制約

- 復元は最新バックアップだけを対象とし、履歴選択・自動保持期限は提供しない。
- 個別drop-in削除は自動復元しない。service削除時の一式バックアップからは復元できる。
- symlink先、発見起点外、他ユーザー所有のservice・drop-inは変更しない。
- `systemd-analyze --recursive-errors=no`を利用するため、編集機能の第一対象はsystemd 257以上を搭載するUbuntu 26.04 LTSとする。
- user busを利用不能にした縮退状態では、編集・drop-in・削除・復元を提供せずread-onlyに縮退する。
