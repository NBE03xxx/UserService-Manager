# 設計判断記録

## ADR-001: 発見範囲と参照先判定を分離する

**決定:** サービス発見は `~/.config/systemd/user/` を起点とし、追加ディレクトリは参照先の管理可能性判定だけに使う。

**理由:** ホーム全体の無差別検索と未登録ファイルの誤検出を避け、挙動を予測可能にする。

## ADR-002: 管理は明示登録制とする

**決定:** 発見しただけでは変更操作の対象にせず、ユーザーの登録を必要とする。登録情報は次回起動へ保持し、消失した unit は再スキャンで除外する。

## ADR-003: 不明な参照は表示のみに倒す

**決定:** ホーム外参照だけでなく、リンク切れ、循環、解析不能など安全を証明できない状態も read-only とする。

**理由:** systemd の全展開規則を不完全に模倣して誤って操作を許可するより安全である。

## ADR-004: v0.1 は操作と閲覧に限定する

**決定:** 作成、編集、削除、drop-in、バックアップ、構文検証を後続へ延期する。

**理由:** ファイル変更は復旧・検証設計を伴うため、基本操作の安全性と分離して段階導入する。

## ADR-005: UI と systemd をポートで分離する

**決定:** UI は backend 非依存の unit/capability モデルを使う。

**理由:** timer/socket/path と cron の追加、テスト用 mock、D-Bus/CLI 選択を容易にする。

## ADR-006: 言語は英語フォールバックとする

**決定:** 日本語 locale は日本語、それ以外は英語。文字列を初期版から分離し、設定には将来の手動選択を予約する。

## ADR-007: 信頼できるシステム実行基盤を役割別に許容する

**決定:** `/usr/bin/python3` 等の領域外参照を一律に拒否しない。Ubuntu のパッケージ管理下、root 所有、一般ユーザー書換不能という信頼基準を満たす system runtime は許容し、ユーザーワークロードと設定の所在を別に評価する。

**例:** `ExecStart=/usr/bin/python3 /home/alice/MyApp/app.py` は、Python とスクリプトの双方が各基準を満たせば管理可能とする。

## ADR-008: 読込エラーのユニットを表示専用候補にする

**決定:** 発見起点にあるが systemd が正常に読み込めない `.service` は非表示にせず、エラー理由付きの表示専用候補として示す。

## ADR-009: 見つからない登録を保持する

**決定:** 登録済み unit が一時的に見つからない場合は `missing` として登録を保持し、操作を禁止する。再出現時は自動復元し、明示的な登録解除でのみ永続情報を削除する。

## ADR-010: Ubuntu 26.04 LTS を第一検証環境とする

**決定:** 初期開発と受入試験は Ubuntu 26.04 LTS、GNOME、Wayland を優先する。それ以前の LTS を含む最低対応版は、依存ライブラリと配布方式の技術調査後に決定する。

## ADR-011: 午後の喫茶店をビジュアルコンセプトとする

**決定:** UI は「おしゃれな午後の喫茶店でのひととき」をコンセプトとし、温かな色、余白、控えめな質感で表現する。GNOME/libadwaita の慣習、アクセシビリティ、状態の意味を優先し、装飾目的の独自部品や過剰なテーマ化は避ける。

**検証:** ライト・ダーク、主要状態、日本語・英語の代表モックアップと、コントラスト測定によって受け入れる。

## ADR-012: 外観はシステム追従を既定とし手動指定を許可する

**決定:** 外観設定は `system`、`light`、`dark` の3値とする。初期値は `system` でGNOME/GTKの外観設定へ追従する。ユーザーが light または dark を選択した場合はシステム設定より優先し、設定を永続化する。

**理由:** デスクトップ全体との一貫性を初期状態で保ちつつ、利用環境や好みに応じた明示選択を可能にするため。

## ADR-013: GTK 4、libadwaita、Python/PyGObjectを採用する

**決定:** v0.1のUIはGTK 4 + libadwaita、実装言語はPython 3 + PyGObject、ビルドはMesonとする。

**理由:** Ubuntu 26.04で必要runtimeが利用でき、GNOME、GIO非同期処理、D-Bus、gettext、外観設定との統合が直接的である。Rustは将来の再評価候補だが、v0.1では開発・配布コストを優先する。

## ADR-014: systemd操作はuser busのD-Bus APIを優先する

**決定:** 状態取得、Start/Stop/Restart、Enable/Disable、Manager.Reloadは `org.freedesktop.systemd1` の構造化APIを第一手段とする。CLIは診断またはD-Busで不足する箇所に限定し、必ずshellを介さず実行する。

## ADR-015: journalはpython-systemdを第一候補とする

**決定:** v0.1はpython-systemdのjournal readerをworkerで使用する。unitとUIDで限定し、cursorと件数上限を持たせる。journalctl JSONはフォールバック候補とする。

## ADR-016: v0.1はnative debで配布する

**決定:** Ubuntu 26.04向け`.deb`を第一配布形式とし、Flatpakは延期する。

**理由:** hostのuser unit、user manager、journalへのアクセスが中核であり、Flatpakでは広い権限が必要となるため。host helper等で適切な境界を作れる場合に再検討する。

## ADR-017: daemon-reloadをuser manager全体の操作とする

**決定:** daemon-reloadは選択unitのread-only状態と切り離す。現在ユーザーのuser managerへ接続中で、全体メニューからユーザーが確認した場合だけManager.Reloadを呼び、完了後に全体を再スキャンする。system managerへフォールバックしない。

## ADR-018: v0.2の編集は直接ファイルと事前検証に限定する

**決定:** 作成先は`~/.config/systemd/user/`直下、編集対象はそこに直接配置された自己所有の通常ファイルに限定する。基本構造検査と`systemd-analyze --user verify`の両方が成功した後だけ保存確認へ進む。

**理由:** symlink先編集、drop-in、自動修正を同時に導入すると対象と復旧範囲が不明確になる。原本と検証済み内容の明確な置換に限ることで、競合検出と復旧を予測可能にする。

## ADR-019: v1.1.0を欠番としv0.2機能をv1.2.0で公開する

**決定:** 誤って使用したv1.1.0は再利用せず欠番とする。v0.2の機能範囲を含む次の公開版はv1.2.0とする。

## 実装前に確定する技術項目

- ExecStart、EnvironmentFile、systemd 指定子の解析範囲
- system runtime のパッケージ由来確認方法と trusted user roots の所有権・モード要件
- journal の既定件数、ページング、追尾方式
- enable 状態（static、indirect、masked 等）の UI 表現
- Ubuntu 26.04通常セッションにおけるD-Bus、journal、GSettingsの実機結果

これらは要件変更ではなく技術スパイクの成果として追記し、安全性に影響する決定は新しい ADR とテストへ反映する。
