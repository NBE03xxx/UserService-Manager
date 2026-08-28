# v0.1 技術スパイク

調査日: 2026-08-25  
第一検証環境: Ubuntu 26.04 LTS (Resolute Raccoon)、GNOME、Wayland

## 1. 結論

| 項目 | v0.1 採用 | 理由 |
|---|---|---|
| UI | GTK 4 + libadwaita | GNOMEとの統合、適応レイアウト、ライト/ダーク・高コントラスト対応 |
| 言語 | Python 3 + PyGObject | Ubuntu 26.04に標準パッケージがあり、GIO/D-Bus/gettextとの統合が直接的 |
| ビルド | Meson | GNOME系アプリの資源、翻訳、デスクトップファイルを一貫して扱える |
| systemd状態・操作 | user bus上の `org.freedesktop.systemd1` D-Bus API | 構造化データ、シェル非依存、非同期呼出し、ジョブ追跡が可能 |
| CLI利用 | 限定的フォールバック／診断 | D-Busで得られない人向け診断等に限定し、シェルを介さない |
| journal | `python3-systemd` のjournal readerをワーカースレッドで使用 | unitフィールドで厳密に絞り、cursor・件数・ページングを扱いやすい |
| 設定 | GSettingsを第一候補 | スキーマ、既定値、変更通知、GNOMEとの統合に適する |
| 初期配布 | Ubuntu向けネイティブ `.deb` | hostのuser manager、journal、ホーム内unitへのアクセスがアプリの本質であり、Flatpakの分離と衝突する |
| Flatpak | v0.1対象外 | 広いfilesystem/session-bus権限が必要。将来はhost helper/portal相当を再検討 |

## 2. 実環境で確認できた基盤

現在のUbuntu 26.04環境では、次が確認できた。

- Python 3.14.4
- GTK 4.22.4 のGObject Introspection
- libadwaita 1.9.1 のGObject Introspection
- PyGObject 3.56.2
- `python3-dbus` 1.4.0
- `python3-systemd` 235
- Flatpak 1.16.6

フェーズAでGNOME/Waylandのsession環境、systemd 259.5、session bus addressを確認した。Codexのコマンド実行sandboxはuser bus接続を拒否したが、通常ログインセッションからPyGObject/Gioでuser manager 259.5へ接続し、Managerと検証unitの構造化プロパティを取得できた。journalも読み取り可能だった。変更操作とjob通知は後続フェーズで確認する。

## 3. GTK 4 + libadwaita

### 採用理由

- `AdwNavigationSplitView` 等で広幅二ペインと狭幅ナビゲーションを統一できる
- `AdwStyleManager` がシステム外観の検出とアプリ側のlight/dark指定を提供する
- 標準widgetがlight、dark、高コントラストへ対応する
- GNOME標準の状態ページ、ダイアログ、リスト、トーストを利用できる

外観設定は次の写像とする。

| アプリ設定 | libadwaita |
|---|---|
| system | システム外観を尊重する値 |
| light | `FORCE_LIGHT` |
| dark | `FORCE_DARK` |

`system` の厳密なenum値は、対象libadwaita 1.9で動作検証して固定する。独自CSSは喫茶店コンセプトに必要な意味トークンへ限定し、success/warning/errorや高コントラストを上書きしない。

## 4. Python/PyGObject と Rust の比較

| 観点 | Python/PyGObject | Rust/gtk-rs |
|---|---|---|
| Ubuntu 26.04環境 | 必要runtimeを確認済み | 現環境にtoolchainなし |
| GTK/libadwaita API | GIで直接利用 | 安全なbinding、型が強い |
| 非同期 | GLib loopとasyncio/GIO awaitableを統合可能 | GLib futureを利用可能だが学習・型の複雑性が高い |
| D-Bus | Gio.DBusProxyを直接利用 | gioまたはzbus等、選択肢が増える |
| 開発速度 | v0.1に有利 | 初期コストが高い |
| 実行時安全性 | 型検査・入力検証・テストで補強が必要 | コンパイル時保証が強い |
| 配布 | OSパッケージ依存を利用可能 | 単一バイナリ寄りだがGTK等は動的依存 |

v0.1はPythonを採用する。ドメイン層に型注釈を必須とし、境界データをdataclass/enumで正規化し、静的型検査、lint、単体試験で動的言語の弱点を補う。性能上重いjournal処理とファイル検査はUIスレッドで実行しない。

## 5. systemd接続

### 基本方式

user bus上の `org.freedesktop.systemd1` をGIOの非同期D-Bus APIで呼ぶ。UIはadapterを介し、D-Busのobject pathやVariantを直接扱わない。

- 状態: Manager/Unit/Service propertiesからLoadState、ActiveState、SubState、Description、FragmentPath、ExecStart等を取得
- 操作: StartUnit、StopUnit、RestartUnit
- enable: GetUnitFileState、EnableUnitFiles、DisableUnitFiles
- daemon-reload: Manager.Reload
- 変更追跡: job返却値または状態変更signalを監視し、完了後に再照会

enable/disableはunit file symlinkを変更する操作であり、状態変更とは別に扱う。実機検証で、D-BusのEnableUnitFiles/DisableUnitFiles後にManager.Reloadが必要かを確認し、必要ならadapter内で一連の操作として実行する。

### daemon-reloadの認可

`daemon-reload` は個別サービスの操作ではなくuser manager全体の操作とする。選択中unitのread-only状態には依存させず、次の条件で許可する。

1. 接続先が現在ユーザーのuser managerである
2. アプリが正常にuser busへ接続している
3. ユーザーが全体メニューから明示選択し確認した

root/system managerへフォールバックしない。完了後は全unitを再スキャンする。

### CLIフォールバック

CLIが必要な場合も `Gio.Subprocess` へ固定argvを渡し、shellを介さない。localeを固定した機械解析に頼るのは避け、可能ならJSON等の安定形式を使う。標準出力・標準エラーには件数・byte・時間の上限を設ける。

## 6. journal

`python3-systemd` のjournal readerを第一候補とする。Ubuntu 26.04のReaderには `this_user()` がないため、現在UIDを取得して `_UID=<uid>` を明示matchする。UIからはJournalPortとして隠し、専用ワーカーで次を行う。

- 現在ユーザーの `_SYSTEMD_USER_UNIT` 等、実機で確認したtrusted fieldでunitを限定
- UIDも合わせ、別ユーザーの同名unit混入を防ぐ
- cursor、件数上限、時刻範囲を使ったページング
- MESSAGEをbinary/巨大入力として扱い、変換と表示に上限を設ける
- cancel要求後は結果をUIへ反映しない

`journalctl --user-unit=…` のJSON出力は、python-systemdが利用不能な環境のフォールバック候補に留める。`--user --unit` と `--user-unit` の意味差があるため、同等と仮定しない。

実機検証では、service自身の出力を `_SYSTEMD_USER_UNIT=target`、user managerの開始・停止messageを `USER_UNIT=target` として取得する必要があった。現在UIDを各OR分岐へ含め、概念上 `(_UID AND _SYSTEMD_USER_UNIT) OR (_UID AND USER_UNIT)` とする。Reader entryの `_UID` は整数として返るためdomain modelでも整数へ正規化する。

## 7. unit発見と読込エラー

発見元は `~/.config/systemd/user/` の `.service` とsymlinkに限定する。ファイル名をcanonical unit IDとして検証後、D-Busでロード状態を問い合わせる。

- loaded: 通常候補
- error/not-found/bad-setting等: 理由付き表示専用候補
- masked: 生状態を保持し、操作capabilityを個別算出
- 起点外の孤立ファイル: 候補外

systemdはinactive unitを常時メモリに保持しないため、メモリ上のunit一覧だけを発見根拠にしない。ディスク起点と問い合わせ結果を組み合わせる。

## 8. パス・runtime信頼判定

参照先はD-Busの正規化済みpropertiesを優先し、unit原文の完全なshell/systemd構文を独自再実装しない。`ExecStart` のargvを役割分類し、次を満たすsystem runtimeを許容する。

- 絶対パスを解決できる
- root所有
- group/other書込み不可
- Ubuntu/Debianパッケージ由来を確認できる、または明示した信頼ディレクトリ・所有権基準を満たす

Ubuntu 26.04実機では `/usr/bin/python3` がroot所有・group/other書込不可・`python3-minimal`由来であることを確認できた。パッケージ由来は `dpkg-query -S` 相当で取得可能だった。実装では解決前後のpathを検証し、操作直前に再評価する。分類不能、環境展開、specifier、wrapperチェーンは安全を証明できなければread-onlyとする。

## 9. 設定と状態

GSettingsを第一候補とし、次を保存する。

- schema version
- registered unit IDsとmissing状態に必要なmetadata
- trusted user roots
- appearance preference (`system/light/dark`)
- language preference予約値 (`system`, 将来`ja/en`)

登録情報は認可キャッシュとして信頼せず、操作直前に再評価する。GSettings schemaのインストールとportableなテスト方法をMeson/パッケージ試作で確認する。

## 10. 配布方式

### v0.1: native deb

Ubuntu 26.04向けの`.deb`を第一成果物とする。依存はディストリビューションのGTK、libadwaita、PyGObject、python3-systemdを使う。アプリ本体、desktop entry、AppStream metadata、icons、GSettings schema、gettext catalogをMesonから配置する。

### Flatpakを延期する理由

Flatpakは既定でhostのホーム、プロセス、journal、session busを制限する。本アプリはhost側の `~/.config/systemd/user/`、user manager D-Bus、journalへのアクセスが本質であり、広いfilesystem権限やbus権限を与えるとsandboxの価値が小さくなる。v0.1ではnative packageを優先し、将来host helperまたは適切なportalが成立する場合に再検討する。

## 11. 実装前の実機検証結果

1. user busのbus name/object/interface: 確認済み
2. Start/Stop/RestartのJobRemoved: 確認済み（意図的timeout/cancelは実装試験へ継続）
3. Enable/Disable、Reload、masked等: 確認済み
4. load-error unit: bad-settingとして確認済み
5. python-systemdのUID/unit OR matchとcursor: 確認済み
6. `AdwStyleManager` のsystem/light/dark: 通常sessionで確認済み
7. dpkg由来・所有権・symlink差替え: 確認済み
8. GSettings専用schema: 確認済み。`.deb`統合は製品build段階へ継続

詳細と非ブロッキング項目は `VALIDATION_RESULTS.md` を参照。検証用unitは全て除去済みである。

## 12. 参照した公式資料

- [systemd D-Bus API](https://github.com/systemd/systemd/blob/main/man/org.freedesktop.systemd1.xml)
- [systemctl semantics](https://github.com/systemd/systemd/blob/main/man/systemctl.xml)
- [systemd unit load behavior](https://github.com/systemd/systemd/blob/main/man/systemd.xml)
- [systemd unit files](https://github.com/systemd/systemd/blob/main/man/systemd.unit.xml)
- [systemd journal fields](https://github.com/systemd/systemd/blob/main/man/systemd.journal-fields.xml)
- [Journal file/API guidance](https://github.com/systemd/systemd/blob/main/docs/JOURNAL_FILE_FORMAT.md)
- [PyGObject asynchronous programming](https://pygobject.gnome.org/guide/asynchronous.html)
- [GIO subprocess API](https://api.pygobject.gnome.org/Gio-2.0/class-Subprocess.html)
- [GIO D-Bus API](https://api.pygobject.gnome.org/Gio-2.0/class-DBusConnection.html)
- [libadwaita StyleManager](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.StyleManager.html)
- [libadwaita styles and appearance](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.5/styles-and-appearance.html)
- [Flatpak sandbox permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html)
- [gtk-rs project](https://gtk-rs.org/)
