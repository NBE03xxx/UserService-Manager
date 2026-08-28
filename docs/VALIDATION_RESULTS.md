# Ubuntu 26.04 実機検証結果

開始日: 2026-08-26  
対象環境: Ubuntu 26.04 LTS、GNOME 50.1、Wayland  
状態: 技術スパイク実機検証完了（Pass with documented limitations）

## 1. フェーズA結果

| ID | 判定 | 実結果 | 次の対応 |
|---|---|---|---|
| VAL-ENV-001 | Pass | Ubuntu 26.04 LTS、GNOME Shell 50.1、Wayland、UID 1000を確認 | 第一検証環境として記録 |
| VAL-ENV-002 | Pass with limitation | systemd 259.5、Python 3.14.4、GTK GI 4.22.4、libadwaita GI 1.9.1、PyGObject 3.56.2、python-systemd 235を確認。Meson、gettext、pkg-config、GTK/libadwaita開発packageは未導入 | フェーズB前に必要最小packageと導入影響を提示する |
| VAL-ENV-003 | Pass | Codex sandboxでは遮断されたが、通常ユーザーterminalからGio D-Busでuser manager 259.5へ接続し、構造化プロパティを取得できた | Codex内の遮断は実行環境固有として扱う |
| VAL-ENV-004 | Pass with limitation | `journalctl --user` で読取可能。python-systemd Readerで `_UID=1000` を明示matchし、該当entryを取得できた | user unit固有matchは検証用unit作成後にVAL-JRNで確認 |
| VAL-ENV-005 | Pass with limitation | 候補5ファイルは `~/.config/systemd/user/` に存在しない。D-Bus上のunit名衝突はsandbox制約により未確認 | unit配置前に通常sessionで再確認する |

## 2. 確認したversion

```text
Ubuntu:       26.04 LTS (Resolute Raccoon)
GNOME Shell:  50.1
Session:      Wayland
systemd:      259 (Ubuntu package 259.5-0ubuntu3.4)
Python:       3.14.4
GTK GI:       4.22.4
libadwaita GI: 1.9.1
PyGObject:    3.56.2
python-systemd: 235
Flatpak:      1.16.6
```

## 3. journal APIに関する発見

Ubuntu 26.04の `python3-systemd` が提供する `journal.Reader` には `this_user()` が存在しない。ユーザー限定は次の考え方へ変更する。

1. 現在UIDをOS APIから取得する
2. Readerへ `_UID=<current uid>` を明示matchする
3. 検証後に `_SYSTEMD_USER_UNIT=<canonical unit>` 等のtrusted fieldを追加matchする
4. `seek_tail()` 後の逆方向取得では `get_previous()` を使う

UID match後のentryで `_UID=1000` と `_SYSTEMD_USER_UNIT` fieldの存在を確認できた。具体的なunit限定、OR/AND match構造、cursorページングはフェーズEで確定する。

## 4. sandbox制約

user bus socketと環境変数は存在するが、Codexのコマンド実行sandboxがローカルtransport接続を拒否した。これはuser managerの不在や一般ユーザー権限不足を示す結果ではない。

```text
Failed to connect to user scope bus via local transport:
Operation not permitted
```

この制約下でD-Bus操作の成否を推測しない。フェーズC/Dへ進む前に、通常のGNOME sessionでVAL-ENV-003とunit名衝突を再確認する。

## 5. 不足している開発package

読み取りで次が未導入と判明した。

- Meson
- gettext
- pkg-config
- GTK 4 development package
- libadwaita development package
- Python development package（状態表示上、導入済みと確認できず）

PyGObjectによる最小runtime検証だけならdevelopment packageの全てが必要とは限らない。フェーズBの検証内容を先に固定し、必要最小限だけを提示する。package導入はシステム変更なので、ユーザーの明示承認なしに行わない。

## 6. 作成・変更・後片付け

- 作成した検証用unit: なし
- 作成した検証用ファイル: なし
- start/stop/restart: 未実施
- enable/disable/daemon-reload: 未実施
- GSettings変更: なし
- journal変更: なし
- 後片付け: 不要

## 7. フェーズA総合判定

**Pass with limitation / Partially blocked**

GTK/Python/journalの基盤は確認できた。D-Bus接続はsandboxにより未評価であり、検証用unit配置へ進む前のゲートとして残す。次はフェーズBのうち、既存runtimeだけで可能なGTK/libadwaita import・初期化の読み取り寄り確認と、検証用資材案の作成を行うのが安全である。GUI起動、GSettings schema作成、package導入は対象を提示してから実行する。

## 8. フェーズB結果

| ID | 判定 | 実結果 | 次の対応 |
|---|---|---|---|
| VAL-UI-001 | Pass | 通常Wayland sessionで検証画面が起動し、表示に問題がないことをユーザーが確認 | 完了 |
| VAL-UI-002 | Pass | 初期状態がGNOMEのダーク設定に従うことをユーザーが確認 | 完了 |
| VAL-UI-003 | Pass | ライト／ダークを再起動なしで切り替えられることをユーザーが確認 | 完了 |
| VAL-UI-004 | Pass | 「システム設定に従う」へ戻せることをユーザーが確認 | GNOME設定を変更した瞬間の追従通知は製品試作でも再確認する |
| VAL-UI-005 | Pass | 専用schemaをstrict compileし、隔離keyfile backendで保存・別process復元に成功。通常sessionでも再起動後の選択保持をユーザーが確認 | 実アプリ方式の標準GSettings backendは製品試作時に再確認する |
| VAL-UI-006 | Pass with limitation | GNOMEの高コントラスト=false、animation=trueを読取。AdwStyleManagerのhigh-contrast状態表示を検証UIへ実装 | 高コントラストと視覚効果低減時の画面は目視確認する |
| VAL-UI-007 | Blocked | gettext/msgfmtが未導入のため翻訳catalog検証は未実施 | package導入計画後に実施する |

## 9. フェーズB検証資材

製品コードと分離して次を作成した。

```text
work/validation/ui/README.md
work/validation/ui/appearance_probe.py
work/validation/ui/io.github.userservicemanager.Validation.gschema.xml
work/validation/ui/gschemas.compiled
work/validation/ui/config/glib-2.0/settings/keyfile
```

検証アプリ/schema IDは `io.github.userservicemanager.Validation`、設定pathは `/io/github/userservicemanager/validation/`。keyfile backendとプロジェクト内のconfig directoryを使ったため、通常のdconf databaseは変更していない。検証設定は最終的に `system` へ戻した。

検証UIが扱うのは外観3択、有効外観、高コントラスト状態だけである。systemd、journal、networkへは接続せず、通常sessionで起動してもservice状態を変更しない。

## 10. フェーズB総合判定

**Pass with limitation**

採用runtimeのimport、実ウィンドウ、外観切替、schema、隔離設定の永続化は成立した。高コントラスト・視覚効果低減の切替時確認とgettextは未完了である。gettextは必要packageの導入承認後に行う。

## 11. 現在までの変更と後片付け

- systemd unit作成・操作: なし
- user manager操作: なし
- 通常dconf/GSettings変更: なし
- project内の使い捨て検証資材: 作成済み
- 検証用keyfile値: `system`
- package導入: なし
- journal変更: なし

検証資材は後続の通常session確認まで保持する。削除時は上記の明示パスだけを対象とする。

## 12. フェーズC準備結果

次の検証資材を `work/validation/systemd/` に作成した。まだ `~/.config/systemd/user/` へ配置していない。

```text
README.md
workload.py
codex-usm-validation-basic.service
codex-usm-validation-python.service
codex-usm-validation-load-error.service
codex-usm-validation-missing.service
codex-usm-validation-symlink-target.service
```

`workload.py` はnetworkへ接続せず、ホーム外へ書き込まず、開始・最大5回のheartbeat・停止だけを標準出力へ書く。1秒の直接実行試験でSIGTERMを受けて正常終了した。

正常4定義と意図的load-error定義に対して `systemd-analyze verify --user` を試みたが、Codex sandboxのsocket制限によりparser結果へ到達する前に終了した。

```text
Failed to turn off SO_PASSRIGHTS on user lookup socket: Operation not permitted
Failed to enable SO_PASSCRED on handoff timestamp socket: Operation not permitted
```

したがってunit定義の公式検証は未評価とし、通常sessionで配置前に再実行する。sandbox内の失敗をunit定義の失敗とは判定しない。

### 配置予定対象

承認後、通常sessionで衝突を再確認してから、次だけを配置またはlinkする。

- `~/.config/systemd/user/codex-usm-validation-basic.service`
- `~/.config/systemd/user/codex-usm-validation-python.service`
- `~/.config/systemd/user/codex-usm-validation-load-error.service`
- `~/.config/systemd/user/codex-usm-validation-missing.service`
- `~/.config/systemd/user/codex-usm-validation-symlink.service` → project内のsymlink target

この時点ではenable/startを行わず、配置後のManager.Reloadとload state確認を最初の状態変更群とする。

## 13. フェーズC 配置・読込結果

実行日: 2026-08-26  
実行方法: 通常GNOME sessionのユーザーterminalから専用scriptを実行

衝突確認と正常4定義の事前検証後、明示5件を `~/.config/systemd/user/` に配置し、user managerをreloadした。start/enableは行っていない。

| Unit | LoadState | ActiveState/SubState | UnitFileState | 判定 |
|---|---|---|---|---|
| codex-usm-validation-basic.service | loaded | inactive/dead | disabled | 期待どおり |
| codex-usm-validation-python.service | loaded | inactive/dead | disabled | 期待どおり |
| codex-usm-validation-load-error.service | bad-setting | inactive/dead | disabled | 意図的エラーを識別できた |
| codex-usm-validation-missing.service | loaded | inactive/dead | disabled | 期待どおり |
| codex-usm-validation-symlink.service | loaded | inactive/dead | alias | ホーム内targetへのsymlinkを認識できた |

### 検証ケース判定

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-DISC-001 | Pass | 正常unitを配置・reload後、loaded/inactive/deadを取得 |
| VAL-DISC-002 | Pass | ExecStartを持たない意図的エラーunitがbad-settingとなった |
| VAL-DISC-003 | Pending | 起点外の孤立serviceが候補外となることはアプリ発見ロジック実装時に確認 |
| VAL-DISC-004 | Pending | masked fixtureはまだ作成していない |
| VAL-DISC-005 | Pending | missing unitの除去・再配置はまだ行っていない |

### 既存unitの警告

事前検証時、既存の `/usr/lib/systemd/user/spice-vdagent.service` に次の警告が表示された。

```text
Unknown key 'StandardError' in section [Install], ignoring.
```

これは今回の検証unitではなくUbuntu環境の既存package unitに関する警告である。変更・修正は行わず、今回の正常4定義のload結果が全てloadedであることから本検証への影響なしと判断した。

### 現在の変更状態

- 検証用unit配置: 5件
- active unit: 0件
- enabled unit: 0件（symlink fixtureのUnitFileStateはalias）
- user manager reload: 実施済み
- 既存unitの変更: なし

## 14. D-Bus直接照会結果

実行日: 2026-08-26  
実行方法: 通常GNOME sessionのユーザーterminalからPyGObject/Gioを使用

user session bus上の `org.freedesktop.systemd1` へ接続し、Managerと各Unitのプロパティを直接取得した。

```text
Manager Version=259.5-0ubuntu3.4
Manager Architecture=x86-64
```

正常4件は `loaded/inactive/dead`、意図的エラーは `bad-setting/inactive/dead` だった。通常配置3件は `disabled`、symlink fixtureは `alias` だった。Description、FragmentPath、Idも期待値と一致した。

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-DBUS-001 | Pass | Manager.LoadUnitとProperties.GetAllで全対象の構造化状態を取得できた |
| VAL-ENV-003 | Pass | 通常sessionからuser managerへ一般ユーザー権限で接続できた |

本照会はStartUnit、StopUnit、RestartUnit、EnableUnitFiles、DisableUnitFiles、Manager.Reloadを呼んでいない。状態変更は発生していない。

## 15. D-Bus Start/Stop/Restart結果

実行日: 2026-08-26  
対象: basic fixture、Python fixtureのみ

全操作でManagerの `JobRemoved` signalを受信し、resultが `done` であることを確認した。操作直後のUnit propertiesも期待値と一致した。

```text
basic:  inactive/dead → StartUnit → active/running → StopUnit → inactive/dead
python: inactive/dead → StartUnit → active/running
        → RestartUnit → active/running → StopUnit → inactive/dead
```

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-DBUS-002 | Pass | StartUnitのJobRemoved=done、active/runningを確認 |
| VAL-DBUS-003 | Pass | StopUnitのJobRemoved=done、inactive/deadを確認 |
| VAL-DBUS-004 | Pass | RestartUnitのJobRemoved=done、active/runningへの復帰を確認 |
| VAL-DBUS-008 | Partial | 正常jobの待機上限を実装。意図的timeout/cancel/errorは未検証 |

enable/disable、Manager.Reloadはこの操作scriptに含めていない。終了処理でも両fixtureがinactive/deadであることを確認済み。

## 16. journal 初回読取結果

実行日: 2026-08-26  
方式: python-systemd Readerおよび比較用 `journalctl --user-unit`

### match式

user manager自身の開始・停止messageは `_SYSTEMD_USER_UNIT=init.scope` かつ `USER_UNIT=<target>` となり、service process自身の出力は `_SYSTEMD_USER_UNIT=<target>` となる。この両方を現在UIDへ限定するには、概念上次の式が必要である。

```text
(_UID=current AND _SYSTEMD_USER_UNIT=target)
OR
(_UID=current AND USER_UNIT=target)
```

python-systemdではUID matchを各OR分岐へ繰り返す。単純に `_UID` と `_SYSTEMD_USER_UNIT` だけをANDすると、manager messageは取得できない。

### 取得結果

- Python fixture: 開始・停止に関するmanager message 6件
- Basic fixture: 開始・停止に関するmanager message 3件
- Python queryへのBasic fixture混入: 0件
- cursorの一意性: 6/6

最新3件をpage 1とし、その最古cursorへ `seek_cursor()` して逆方向に読んだ場合、anchor自身が最初に再取得された。anchorを1件除外するとpage 2は3件となり、page 1とのcursor重複は0件だった。

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-JRN-001 | Partial | 現在UID・対象unitのmanager message限定に成功。service stdoutは再検証が必要 |
| VAL-JRN-002 | Pass | BasicとPythonを分離し、対象外unit混入0件 |
| VAL-JRN-003 | Pass | cursor境界の重複除去後、3件×2pageで重複0件 |
| VAL-JRN-004 | Pending | logなし・rotationは未検証 |
| VAL-JRN-005 | Pending | 長い/binary messageは未検証 |
| VAL-JRN-006 | Pending | cancelは未検証 |

### workload stdoutに関する制約

Python fixtureのworkloadが出力したheartbeatは初回journalに含まれなかった。この結果を受け、fixtureへ `StandardOutput=journal` と `StandardError=journal` を明示し、次節で再検証した。

## 17. journal workload再検証結果

実行日: 2026-08-26

Python fixtureへ `StandardOutput=journal`、`StandardError=journal` を明示してuser managerをreloadした。更新後も `loaded/inactive/dead` であり、両出力先はjournalとして取得できた。

5秒間のStart/Stopで次を確認した。

```text
codex-usm-validation: started
codex-usm-validation: heartbeat=0
codex-usm-validation: heartbeat=1
codex-usm-validation: heartbeat=2
codex-usm-validation: stopped
```

停止後の状態は `inactive/dead`。python-systemdのOR match式で直近14件を取得し、内訳はworkload 5件、manager 9件、cursor 14件全て一意、別unit混入0件だった。

`_UID` はmatch指定時には文字列を使用するが、Readerのentryでは整数 `1000` として返った。adapter境界で整数へ正規化し、表示文字列との直接比較を避ける。

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-JRN-001 | Pass | 現在UIDに限定し、service自身とmanager双方の対象unitログを統合取得できた |
| VAL-JRN-002 | Pass | 別unit混入0件 |
| VAL-JRN-003 | Pass | cursor一意性とページ境界処理を確認 |

VAL-JRN-004〜006（空/rotation、長い/binary、cancel）は引き続き未検証。

## 18. Enable/Disable/Manager.Reload結果

実行日: 2026-08-26  
対象: `codex-usm-validation-basic.service` のみ

D-Bus Manager APIで次の遷移を確認した。

```text
disabled
→ EnableUnitFiles (carries_install_info=True)
→ enabled
→ Manager.Reload
→ enabled
→ DisableUnitFiles
→ disabled
→ Manager.Reload
→ disabled
```

返されたfilesystem changeは次の1パスだけだった。

```text
enable:  symlink ~/.config/systemd/user/default.target.wants/codex-usm-validation-basic.service
disable: unlink  ~/.config/systemd/user/default.target.wants/codex-usm-validation-basic.service
```

symlink sourceは `~/.config/systemd/user/codex-usm-validation-basic.service`。サービスのStartは行われず、最終UnitFileStateはdisabledである。

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-DBUS-005 | Pass | GetUnitFileStateでdisabled/enabledを生値として取得 |
| VAL-DBUS-006 | Pass | Enable/Disableのstateとsymlink/unlink changeを確認 |
| VAL-DBUS-007 | Pass | Manager.Reloadが成功し、前後のUnitFileStateが維持された |

## 19. missing/masked結果

実行日: 2026-08-26  
対象: missing fixture、intentional load-error fixtureのみ

専用scriptが両定義を一時バックアップし、次の遷移を確認した。

```text
missing fixture:    loaded → not-found → loaded
load-error fixture: bad-setting → masked → bad-setting
```

missing fixtureは一時除去・reload後にnot-foundとなり、元ファイルの再配置・reload後にloadedへ復帰した。load-error fixtureは一時的な `/dev/null` symlink・reload後にmaskedとなり、元の意図的エラー定義へ復元・reload後にbad-settingへ戻った。

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-DISC-004 | Pass | `/dev/null` maskをmaskedとして取得し、生状態を保持できた |
| VAL-DISC-005 | Pass | 除去後not-found、再配置後loadedへの復帰を確認 |

終了時は両ファイルが元の通常ファイルへ復元され、Start/Enableは行っていない。

## 20. パス判定probe（Codex sandbox）

実行日: 2026-08-26

systemdとユーザー設定を変更せず、`work/validation/path/` 内の一時symlinkだけで役割別判定を検証した。一時entryは終了時に全て除去された。

| ケース | 結果 | 期待との一致 |
|---|---|---|
| ホーム内workload | manageable | 一致 |
| ホーム内link → ホーム内workload | manageable | 一致 |
| ホーム内link → 領域外workload | read-only | 一致 |
| 壊れたlink | unknown | 一致 |
| 循環link | unknown | 一致 |
| ユーザー所有ファイルをsystem runtime役割で評価 | read-only | 一致 |
| link判定後にホーム内→領域外へ差替え | manageable → read-only | 一致 |
| `/usr/bin/python3` system runtime | read-only | sandbox制約により不一致 |

`/usr/bin/python3` は `/usr/bin/python3.14` へ解決され、package由来は `python3-minimal` と確認できた。しかしCodex sandbox内ではownerが `nobody` に写像されるため、root所有条件を満たさず安全側のread-onlyになった。判定基準は緩めず、通常sessionで同じprobeを実行してroot所有・非書込・package由来の3条件を再確認する。

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-PATH-001 | Partial | ホーム内workloadはmanageable。system runtime所有者は通常session確認待ち |
| VAL-PATH-002 | Pass | ホーム内link解決後もmanageable |
| VAL-PATH-003 | Pass | 領域外workloadはread-only |
| VAL-PATH-004 | Pass | 壊れた／循環linkはunknown |
| VAL-PATH-005 | Pending | root所有runtimeは通常session確認待ち |
| VAL-PATH-006 | Pass | ユーザー所有runtimeはread-only |
| VAL-PATH-007 | Partial | python3-minimal由来を確認。owner条件と組み合わせたPassは通常session待ち |
| VAL-PATH-008 | Pass | 操作前再評価に相当する再checkで領域外差替えを検出 |

## 21. パス判定probe（通常session）

実行日: 2026-08-26

通常ユーザーterminalから同じprobeを実行し、全ケースが期待どおり成功した。

```text
/usr/bin/python3
→ /usr/bin/python3.14
→ owner=root
→ group/other writeなし
→ package=python3-minimal
→ trusted system runtime / manageable
```

ホーム内workloadとホーム内linkはmanageable、領域外workloadはread-only、壊れた／循環linkはunknown、ユーザー所有runtimeはread-onlyだった。判定後のlink差し替えは再checkでmanageableからread-onlyへ変化した。

| ID | 最終判定 |
|---|---|
| VAL-PATH-001 | Pass |
| VAL-PATH-002 | Pass |
| VAL-PATH-003 | Pass |
| VAL-PATH-004 | Pass |
| VAL-PATH-005 | Pass |
| VAL-PATH-006 | Pass |
| VAL-PATH-007 | Pass |
| VAL-PATH-008 | Pass |

Codex sandboxでのowner=`nobody` は隔離環境固有であり、安全側にread-onlyとした挙動も妥当だった。製品はowner確認不能時に許可へ倒さない。

## 22. 発見起点の限定結果

実行日: 2026-08-26  
方式: `~/.config/systemd/user/` だけを列挙する読み取り専用probe

起点には`.service` entryが6件あり、そのうち検証prefixの5件は全て期待集合と一致した。プロジェクト内に単独で存在する `codex-usm-validation-symlink-target.service` は直接候補に含まれなかった。一方、起点内の `codex-usm-validation-symlink.service` は候補となり、ホーム内のproject targetへ正しく解決された。

| ID | 判定 | 根拠 |
|---|---|---|
| VAL-DISC-003 | Pass | 起点外の単独serviceは直接候補にならず、起点内symlinkだけが候補になった |

probeはホーム全体を検索せず、起点直下のentryだけを読み取った。

## 23. 後片付け結果

実行日: 2026-08-26

専用cleanup scriptで検証用5unitのstop/disableを試行し、明示5ファイル・symlinkを削除してuser managerをreloadした。その後の読み取り確認結果は次のとおり。

```text
~/.config/systemd/user/ の codex-usm-validation-*.service: 0件
配下のenable symlink等 codex-usm-validation-*.service: 0件
隔離GSettings appearance: system
```

- 検証用active unit: なし
- 検証用enabled unit: なし
- 検証用unit file/symlink: なし
- 通常dconf変更: なし
- journal削除: なし
- package導入: なし
- 既存unit変更: なし

project内の `work/validation/` 資材と設計証跡は、再現性のため保持している。これらはuser managerに登録されていない。

## 24. 最終判定

**Pass with documented limitations**

製品実装前の主要技術ゲートは成立した。

- GTK 4/libadwaita/PyGObjectの起動と外観切替
- 隔離GSettingsのschema・永続化
- user manager D-Bus接続と構造化状態取得
- Start/Stop/RestartとJobRemoved
- Enable/Disableとfilesystem change
- Manager.Reload
- loaded/bad-setting/not-found/masked/alias状態
- UID・unit限定journal、workload/managerログ統合、cursorページング
- 発見起点の限定
- system runtime、workload、symlink、TOCTOUの役割別パス判定
- 一般ユーザー権限のみでの動作
- 完全な後片付け

### 製品実装中に継続する非ブロッキング項目

- VAL-UI-006: 高コントラスト・視覚効果低減の目視試験
- VAL-UI-007: gettext catalogのbuild検証
- VAL-DBUS-008: 意図的timeout/cancel/errorの詳細試験
- VAL-JRN-004: logなし・rotation
- VAL-JRN-005: 長い/binary message
- VAL-JRN-006: cancel時の古い結果破棄
- GSettings標準backendと`.deb` package内schemaの統合試験
- Meson/gettext/development package導入後のbuild試験

これらは採用技術の成立を否定するものではなく、該当機能の実装完了条件へ組み込む。製品コード着手前ゲートは完了とする。
