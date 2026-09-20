# v0.3 drop-in・ライフサイクル 受入結果

実施日: 2026-09-20
製品版: v1.3.0（v1.1.0は欠番）
第一検証環境: Ubuntu 26.04 LTS / GNOME / Wayland / systemd 259

## 判定

**v0.3実装受入: 合格。v1.3.0のコミット・push: 承認。**

複数drop-inの一覧・作成・編集・削除、systemd検証、変更差分、停止・無効化済みserviceの耐久化バックアップ付き削除、最新バックアップの非上書き復元を実装・検証した。

## 自動検証

- 単体・契約テスト78件成功
- 要件IDとTEST_PLAN追跡IDの完全一致
- Python compileall成功
- GSettings schema strict dry-run成功
- desktop entry検証成功
- AppStream pedantic検証成功
- Meson configure/build/test/install smoke test成功
- Debian package build中のMeson test成功

## 安全性確認

- drop-in名を安全な`.conf`名に限定し、パス区切り・隠し名・不正文字を拒否
- UTF-8、NUL、256 KiB上限、section/directive構造を保存前検査
- 隔離したserviceとdrop-inを`/usr/bin/systemd-analyze`でshellなし検証
- drop-inディレクトリとファイルのsymlink、他者所有、group/other書込可能を拒否
- SHA-256リビジョン再検査で外部変更を上書き・削除しない
- 新規service・drop-in・復元先は排他的link作成で並行作成時にも上書きしない
- service削除はinactive/failedかつ非enabled、直接配置通常ファイルに限定
- service本体、drop-in、manifestをmode 0700/0600の隠し領域へ保存・fsync後に削除
- 復元先にserviceまたはdrop-inディレクトリがあれば拒否
- 変更後reload失敗はファイル変更済みと分かるエラーへ変換

## Ubuntu 26.04実機受入

`docs/validation/v1_3_lifecycle_acceptance.py`を製品packageのコードで実行し、予約済みの使い捨てunit名で次を通し確認した。

1. service作成、reload、明示登録
2. drop-in作成とsystemd事前検証
3. drop-in編集と追加・削除行を含むunified diff
4. service本体とdrop-in一式のバックアップ付き削除
5. missing状態と最新バックアップの検出
6. service本体とdrop-in一式の非上書き復元
7. mode 0600、reload、再発見
8. 対象unit、drop-in、バックアップ、user manager読込状態の後片付け

製品モードの日本語GUIでメイン行のdrop-in・削除導線、drop-in一覧、作成エディターを確認した。有効なdrop-inを入力して実際のsystemd検証を実行し、検証結果、追加差分、キャンセル／保存を表示する確認画面をGNOME/Wayland上で目視確認した。保存は選択せず、既存serviceに変更がないことを確認した。

## 配布成果物

- ファイル: `user-service-manager_1.3.0_all.deb`
- サイズ: 531776 bytes
- SHA-256: `9b9db6d023937ac50798f8f4508b1127fd1fc46ef43c2f3af9ef5ea1a1299937`
- Ubuntu 26.04 VMへの1.2.0から1.3.0へのupgrade成功
- package内の版番、依存関係、新規domain/port/adapter/application moduleを確認

## 既知の制約

- UIからの復元は最新の有効なバックアップだけを対象とする。
- バックアップの履歴選択、自動削除、保持期限設定は未実装。
- 個別drop-in削除の自動復元は行わない。service削除バックアップにはdrop-in一式を含める。
- symlink先、発見起点外、他ユーザー所有のservice・drop-inは変更しない。

## 後片付け

受入で作成した`codex-usm-v130-validation.service`、drop-in、バックアップ、user managerの読込状態は復元済み。GUIプレビューで使用した`openclaw-gateway.service`にはdrop-inを保存していない。
