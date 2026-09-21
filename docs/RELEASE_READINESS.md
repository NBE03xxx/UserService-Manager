# v1.3.1 リリース準備状況

## 判定

**文書整合性: 合格。文書更新リリース: 承認。**

v1.3.0の機能と安全境界は変更していない。ユーザーの利用目的に合わせ、現在の製品範囲、期限未定の将来構想、実装しない項目を文書全体で整合した。リリースを阻害する未完了項目はない。

## v1.3.1で変更した文書方針

- 一般ユーザーのsystemd `.service`管理を現在の製品範囲として明記
- systemdユニット拡張、関連表示、高度ログ、追加Debian系環境検証を期限未定の将来構想へ変更
- cronバックエンドとアプリ内の手動言語選択を実装計画から除外
- README、要件、テスト計画、ロードマップ、アーキテクチャ、ADR、国際化、引き継ぎ文書を整合
- v1.3.0が公開済みであることをリリース証跡へ反映

## 完了した証跡

- 要件IDとTEST_PLAN追跡IDが完全一致
- 自動テスト79件成功
- GSettings、desktop entry、AppStream検証成功
- Meson configure/build/test/install smoke test成功
- Debian package buildとbuild内test成功
- Ubuntu 26.04 LTS VMへの1.3.1 package upgrade成功
- 製品コードでdrop-in作成・編集・検証・差分・削除バックアップ・復元を通し確認
- 製品モードのメイン画面、drop-in一覧・エディター・差分確認をGNOME/Wayland上で目視確認
- 検証unit、drop-in、バックアップ、user manager読込状態の後片付け完了

詳細は`V1_3_1_RESULTS.md`を参照する。機能受入は`V0_3_RESULTS.md`、それ以前の証跡は`V0_2_RESULTS.md`、`PHASE1_RESULTS.md`〜`PHASE6_RESULTS.md`、`ACCEPTANCE_CHECKLIST.md`に保持している。

## 配布成果物

- version: `1.3.1`
- package: `user-service-manager_1.3.1_all.deb`
- package size: 532000 bytes
- SHA-256: `1145d0cfd44aebc94d4c94473e2bf8a1886355dea9732cbb78081274d32e039f`
- v1.1.0は誤用のため欠番とし、tag・配布版に再利用しない

v1.3.1のtag、GitHub Release、`.deb`、`.sha256`を公開済み。Releaseは<https://github.com/NBE03xxx/UserService-Manager/releases/tag/v1.3.1>。

## 既知の制約

- 復元は最新バックアップだけを対象とし、履歴選択・自動保持期限は提供しない。
- 個別drop-in削除は自動復元しない。service削除時の一式バックアップからは復元できる。
- symlink先、発見起点外、他ユーザー所有のservice・drop-inは変更しない。
- `systemd-analyze --recursive-errors=no`を利用するため、編集機能の第一対象はsystemd 257以上を搭載するUbuntu 26.04 LTSとする。
- user busを利用不能にした縮退状態では、編集・drop-in・削除・復元を提供せずread-onlyに縮退する。
