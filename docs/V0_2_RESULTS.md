# v0.2 作成・編集の安全基盤 受入結果

実施日: 2026-09-20  
製品版: v1.2.0（v1.1.0は欠番）  
第一検証環境: Ubuntu 26.04 LTS / GNOME / Wayland / systemd 259

## 判定

**v0.2実装受入: 合格。v1.2.0配布リリース: 承認。**

`.service`の新規作成、元ファイル編集、事前検証、明示選択バックアップ、原子的保存、user manager reload、再スキャン、外部変更の競合拒否を実装・検証した。

## 自動検証

- 単体・契約テス66件成功
- 要件IDとTEST_PLAN追跡IDの完全一致
- Python compileall成功
- GSettings schema strict dry-run成功
- desktop entry検証成功
- AppStream pedantic検証成功
- Meson configure/build/test/install smoke test成功
- Debian package build中のMeson test成功

## 編集セキュリティ確認

- canonical `.service`名以外を拒否
- UTF-8、NUL、256 KiB上限、directive形式、`[Service]`を保存前検査
- `/usr/bin/systemd-analyze --user --recursive-errors=no verify`をshellなしで実行
- 有効なunit定義を受理し、存在しない`ExecStart`を持つ定義を拒否
- 編集対象のsymlink、非通常ファイル、他者所有、group/other書込可能を拒否
- `O_NOFOLLOW`とdescriptorの`fstat`で読込時の差替えを防止
- SHA-256リビジョンの再検査で外部変更を上書きせず拒否
- mode 0600一時ファイル、同一ディレクトリ内`os.replace`、file/directory fsyncを確認
- 利用者が選択した場合だけmode 0600のタイムスタンプ付きバックアップを作成
- 保存後のreload失敗は「ファイルは保存済み」と分かるエラーに変換

## Ubuntu 26.04実機受入

`docs/validation/v1_2_editing_acceptance.py`を使い、予約済みの使い捨てunit名で次を通し確認した。

1. 新規作成とsystemd事前検証
2. user manager reloadと再発見
3. mode 0600の対象ファイル
4. バックアップ付き編集と元内容の保持
5. 外部変更後の競合拒否
6. 対象unitとバックアップの完全削除、reload

製品モードのメイン画面で作成ボタンと行ごとの編集ボタンを確認した。`Ctrl+N`で日本語のサービスファイルエディターが開き、unit名、全文エディター、「検証して保存」をダーク表示で目視確認した。

## 配布成果物

- ファイル: `user-service-manager_1.2.0_all.deb`
- サイズ: 524840 bytes
- SHA-256: `bdbb081ba1bfe9055523508901743d28c42947a91e859dd2bec4ce4ba0cf24fc`
- Ubuntu 26.04 VMへのinstall/reinstall成功
- package内の版番、依存関係、新規editing moduleを確認

## 後片付け

受入で作成した`codex-usm-v120-validation.service`、バックアップ、user managerの読込状態は復元済み。検証unitの残留がないことを確認した。
