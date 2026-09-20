# v1.2.0 リリース準備状況

## 判定

**実装受入: 合格。配布リリース: 承認。**

v1.0.1までの閲覧・操作・journal・国際化・アクセシビリティの受入に加え、v0.2の作成・編集の安全基盤をUbuntu 26.04 LTSで受入した。未完了のリリース阻害項目はない。

## v1.2.0で追加した機能

- `.service`の新規作成と元ファイル編集
- UTF-8、サイズ、基本構造の事前検査
- systemd自身によるステージ済み内容の事前検証
- 利用者選択のタイムスタンプ付きバックアップ
- SHA-256リビジョンによる外部変更の競合拒否
- mode 0600一時ファイルからの原子的置換
- 保存後のuser manager reloadと再スキャン
- 日本語・英語エディター、作成・編集ボタン、`Ctrl+N`ショートカット

## 完了した証跡

- 要件IDとTEST_PLAN追跡IDが完全一致
- 自動テス66件成功
- GSettings、desktop entry、AppStream検証成功
- Meson configure/build/test/install smoke test成功
- Debian package buildとbuild内test成功
- Ubuntu 26.04 LTS VMへのpackage install/reinstall成功
- systemd 259で有効なunitの受理と無効な`ExecStart`の拒否を確認
- 使い捨てunitで作成、編集、バックアップ、reload、再発見、競合拒否を通し確認
- 製品モードのメイン画面と日本語エディターをGNOME/Wayland上で目視確認
- 検証unit、バックアップ、user manager読込状態の後片付け完了

詳細は`V0_2_RESULTS.md`を参照する。v1.0.1までの証跡は`PHASE1_RESULTS.md`〜`PHASE6_RESULTS.md`と`ACCEPTANCE_CHECKLIST.md`に保持している。

## 配布成果物

- version: `1.2.0`
- package: `user-service-manager_1.2.0_all.deb`
- package size: 524840 bytes
- SHA-256: `bdbb081ba1bfe9055523508901743d28c42947a91e859dd2bec4ce4ba0cf24fc`
- v1.1.0は誤用のため欠番とし、tag・配布版に再利用しない

## 公開方法

v1.2.0は正式tagとGitHub Releaseを使用し、`.deb`とSHA-256 checksumを添付する。本文書の承認済みcommitをtag対象とする。

## 既知の制約

- 編集は発見起点に直接配置された安全な通常ファイルに限定し、symlink先は編集しない。
- service削除、自動復元、drop-in、差分プレビューはv0.3へ送る。
- `systemd-analyze --recursive-errors=no`を利用するため、v1.2.0の編集機能の第一対象はsystemd 257以上を搭載するUbuntu 26.04 LTSとする。
- user busを意図的に利用不能にした縮退状態では、編集とreloadを提供せずread-onlyに縮退する。
