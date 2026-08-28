# Ubuntu 26.04 実機検証計画

作成日: 2026-08-26  
対象: Ubuntu 26.04 LTS、GNOME、Waylandの通常ログインセッション  
位置づけ: 製品実装前の技術検証。製品コードではない。

## 1. 目的

`TECHNICAL_SPIKE.md` で採用した技術が通常のデスクトップセッションで成立することを、小さく隔離された検証用資材で確認する。確認結果は `VALIDATION_RESULTS.md` に残し、要件、ADR、アーキテクチャ、テスト計画へ反映する。

主な検証対象は次のとおり。

- GTK 4、libadwaita、PyGObject、GSettings、gettext
- system/light/darkとシステム外観追従
- user managerのD-Bus接続・状態取得・操作・ジョブ通知
- python-systemdによるjournalのunit/UID限定とページング
- unitの発見、load-error、masked、missing、再出現
- Python等のsystem runtimeとホーム内workloadの役割別判定
- symlink、所有権、書込み権限、TOCTOUに対する安全側の判定

## 2. 安全原則

1. root、`sudo`、Polkitによる昇格を使わない。
2. system serviceを操作せず、現在ユーザーのuser managerだけを対象とする。
3. 既存unitを変更せず、固有prefixを持つ検証用unitだけを操作する。
4. 検証資材はプロジェクトの検証用ディレクトリと `~/.config/systemd/user/` 内の固有名に限定する。
5. unit配置、enable、start等の状態変更前に、対象と影響を再提示してユーザー確認を得る。
6. 各状態変更前後に状態を記録し、後片付け可能性を確認する。
7. 検証失敗時は次の操作へ進まず、安全な停止・disable・ファイル除去を優先する。
8. 既存のjournalを削除・変更しない。読み取りだけを行う。
9. 検証用processはネットワークへ接続せず、ホーム外へ書き込まない。
10. 検証中に作成した永続物を一覧化し、終了時に明示的に除去する。

## 3. 検証用の名前と配置

実行時に衝突がないことを再確認し、次の名前を第一候補とする。

```text
Unit prefix: codex-usm-validation-
Unit directory: ~/.config/systemd/user/
Work directory: <project>/work/validation/
Evidence directory: <project>/work/validation/evidence/
```

候補unit:

- `codex-usm-validation-basic.service`
- `codex-usm-validation-python.service`
- `codex-usm-validation-load-error.service`
- `codex-usm-validation-symlink.service`
- `codex-usm-validation-missing.service`

実行前に同名unit、同名ファイル、既存登録状態がないことを読み取り専用操作で確認する。存在する場合は上書きせず、別のランダムsuffixを選ぶ。

## 4. 証跡

検証結果ごとに次を記録する。

- 検証ID、実行日時、実行者
- Ubuntu、GNOME、Wayland、systemd、GTK、libadwaita、Pythonのversion
- 事前状態、実行内容、期待結果、実結果
- 成否、エラー分類、関連要件ID・テストケースID
- 作成したファイル・unit・設定
- 後片付け結果

秘密値、完全な環境変数、無関係なjournal本文は保存しない。unit名と検証用メッセージだけを証跡に含める。

## 5. フェーズA — 読み取り専用の環境確認

| ID | 確認 | 期待結果 |
|---|---|---|
| VAL-ENV-001 | OS、desktop、session type、version | Ubuntu 26.04、GNOME、Waylandとして記録できる |
| VAL-ENV-002 | GTK 4、libadwaita、PyGObject、python-systemd、Meson | 採用versionを読み取れる。不足時は変更せず報告する |
| VAL-ENV-003 | user busと `org.freedesktop.systemd1` | 現在ユーザーのmanagerへ一般権限で接続できる |
| VAL-ENV-004 | journal読取可否 | 現在UIDを明示matchし、利用可能な範囲を読み取れる |
| VAL-ENV-005 | 検証用unit名の衝突確認 | 候補名が未使用、または代替suffixを選べる |

**ゲートA:** 全て読み取り専用。不足・接続不能があればここで停止し、環境整備案だけを提示する。

## 6. フェーズB — GTK/libadwaita/GSettings最小検証

製品画面ではなく、外観と設定APIだけを確認する使い捨ての最小検証プログラムを、`work/validation/` 内に作成する。プロジェクトの製品ソース構成には置かない。

| ID | 確認 | 期待結果 |
|---|---|---|
| VAL-UI-001 | GTK 4 + Adw.Application起動 | Wayland上で一般ユーザーとして起動する |
| VAL-UI-002 | system外観 | GNOMEのlight/dark設定を反映する |
| VAL-UI-003 | FORCE_LIGHT/FORCE_DARK | 再起動なしで切り替わる |
| VAL-UI-004 | systemへ戻す | システム設定へ再追従する |
| VAL-UI-005 | GSettings保存・再起動 | `system/light/dark` が保持・復元される |
| VAL-UI-006 | 高コントラスト・視覚効果低減 | 標準設定を尊重し情報が失われない |
| VAL-UI-007 | gettext ja/en | UI文字列を日本語・英語で切り替えて表示できる |

**ゲートB:** ファイル作成とGUI起動前に内容を提示する。GSettings schemaは検証用IDを使い、既存schemaを変更しない。

## 7. フェーズC — 検証用unitの配置と発見

検証用workloadは、一定間隔で固有の短いメッセージをjournalへ出力し、終了signalを正常処理する。ネットワーク通信、外部入力、ホーム外書込みを行わない。

| ID | 確認 | 期待結果 |
|---|---|---|
| VAL-DISC-001 | 正常unitを起点へ配置してreload | user managerがloadedとして認識する |
| VAL-DISC-002 | 意図的な構文不正unit | load-error/bad-setting等を取得し、表示専用に分類できる |
| VAL-DISC-003 | 起点外の孤立service | 発見候補に含まれない |
| VAL-DISC-004 | 0 byteまたは `/dev/null` mask | masked状態を二値化せず取得できる |
| VAL-DISC-005 | unit削除・reload・再配置 | missing保持と再出現を識別できる |

**ゲートC:** unit内容、配置先、作成対象を提示して確認を得る。既存unitは変更しない。

## 8. フェーズD — D-Bus状態取得と操作

| ID | 確認 | 期待結果 |
|---|---|---|
| VAL-DBUS-001 | properties取得 | LoadState、ActiveState、SubState、Description、FragmentPath、ExecStartを構造化取得できる |
| VAL-DBUS-002 | StartUnit | jobを追跡しactive到達を確認できる |
| VAL-DBUS-003 | StopUnit | jobを追跡しinactive到達を確認できる |
| VAL-DBUS-004 | RestartUnit | instance/job変化とactive復帰を確認できる |
| VAL-DBUS-005 | GetUnitFileState | enabled/disabled/static/masked等を生値で取得できる |
| VAL-DBUS-006 | EnableUnitFiles/DisableUnitFiles | symlink変更を確認し、Reload要否を特定できる |
| VAL-DBUS-007 | Manager.Reload | user managerだけをreloadし、全体再照会できる |
| VAL-DBUS-008 | timeout/cancel/error | UIを塞がないadapter方針に必要な結果を得る |

**ゲートD:** start/stop/restart/enable/disable/reloadは状態変更である。各操作群の直前に対象を示して確認を得る。system busやsystem managerへは接続しない。

## 9. フェーズE — journal

| ID | 確認 | 期待結果 |
|---|---|---|
| VAL-JRN-001 | user unit fieldとUID match | 対象unit・現在UIDのメッセージだけ取得できる |
| VAL-JRN-002 | 別unitの同時出力 | 対象外メッセージが混在しない |
| VAL-JRN-003 | cursorページング | 重複・欠落なく既定件数単位で移動できる |
| VAL-JRN-004 | logなし・rotation | 空状態または継続可能な状態として扱える |
| VAL-JRN-005 | 長い/binary message | 上限付きで安全に表示用データへ変換できる |
| VAL-JRN-006 | cancel | 取消後の古い結果をUI状態へ反映しない設計にできる |

読み取りにはpython-systemdを第一候補とし、`journalctl --user-unit` JSONはフォールバック比較だけに使う。

## 10. フェーズF — パスとsystem runtimeの信頼判定

| ID | 確認 | 期待結果 |
|---|---|---|
| VAL-PATH-001 | `/usr/bin/python3` + ホーム内script | runtimeとworkloadを分離しmanageableとなる |
| VAL-PATH-002 | ホーム内symlink→ホーム内 | 解決後もmanageableとなる |
| VAL-PATH-003 | ホーム内symlink→領域外workload | read-onlyとなる |
| VAL-PATH-004 | 壊れた/循環symlink | unknown/read-onlyとなる |
| VAL-PATH-005 | root所有・非書込runtime | 信頼条件を確認できる |
| VAL-PATH-006 | 一般ユーザー書込可能なruntime模擬 | 信頼せずread-onlyとなる |
| VAL-PATH-007 | dpkg由来確認 | package所有情報を安全に取得できる |
| VAL-PATH-008 | 判定後のsymlink差替え | 操作直前の再検証で拒否できる |

TOCTOU試験は検証用リンクだけを対象とし、既存ファイルを差し替えない。

## 11. 後片付け

実行時には解決済みの明示的な検証unit名とパスだけを対象にし、次の順で行う。

1. 検証用unitをstop
2. 検証中にenableしたunitをdisable
3. user managerへdaemon-reload
4. 検証用unitがinactive/not-foundであることを確認
5. `~/.config/systemd/user/` 内の検証用ファイル・symlinkだけを除去
6. 検証用GSettings値/schemaを検証方式に応じて除去
7. `work/validation/` の資材は証跡確認後に、ユーザーの了承を得て削除または保持
8. 既存unitとアプリ設定に差分がないことを確認

削除前に対象を列挙し、prefixの曖昧なglobやホーム全体への再帰削除を使わない。journalは削除しない。

## 12. 中止条件と復旧

次の場合は直ちに次フェーズへ進まない。

- 接続先がuser managerであることを証明できない
- 検証用以外のunitへ変更が及ぶ可能性がある
- 既存同名ファイル、設定、symlinkを発見した
- root/Polkit認証を要求された
- stop/disableが失敗し検証processが残った
- unit名、パス、UIDが期待と異なる
- journalや出力が上限なく増える

復旧は読み取り確認、検証用unitのstop/disable、明示対象だけの除去、reloadの順とする。復旧できない場合は破壊的操作を追加せず、状態と手動対処手順を報告する。

## 13. 結果判定

| 判定 | 条件 |
|---|---|
| Pass | 期待結果を満たし、後片付け完了 |
| Pass with limitation | 安全に利用可能だがversion・状態等の制約が判明 |
| Fail | 採用方式で期待結果を満たさない |
| Blocked | 環境・権限・接続条件により検証不能 |

全フェーズ完了後に `VALIDATION_RESULTS.md` を作成する。Failまたは重要なlimitationがある場合は製品コードへ進まず、`TECHNICAL_SPIKE.md`、ADR、要件、テスト計画を更新して再レビューする。

## 14. 要件・テストとの対応

| 検証群 | 主な要件・テスト |
|---|---|
| VAL-ENV | NFR-001〜003、SEC-001、TC-ERR-001 |
| VAL-UI | UI-005〜006、I18N-001〜003、TC-UI-003〜006、TC-I18N-001〜002 |
| VAL-DISC | FR-001〜005、TC-DISC-001〜004 |
| VAL-DBUS | FR-006〜010、FR-017、SEC-002〜005、TC-LIST-001、TC-OPS-001〜004 |
| VAL-JRN | FR-011、SEC-007、TC-LOG-001、TC-SEC-004 |
| VAL-PATH | FR-012〜015、SEC-003〜004、TC-PATH-001〜006、TC-SEC-002 |

## 15. 実行承認の境界

この文書の作成は、検証用ファイルの作成、unit配置、systemd操作、GSettings変更を承認するものではない。次のターンではまずフェーズAの読み取り専用確認だけを行う。フェーズB以降は、作成・変更対象と後片付け方法を提示してから進める。
