# フェーズ2 実装・検証結果

## 1. 状態

フェーズ2のうち、サービスファイルの限定発見、systemd user managerとの読み取り照合、明示登録、登録解除、missing保持、登録情報のGSettings永続化を実装した。通常のWaylandユーザーセッションにおける読み取り統合確認も成功したため、フェーズ2は2026-08-26に完了した。実サービスに対するstart/stop等の変更操作は接続していない。

## 2. 実装した範囲

- `~/.config/systemd/user/` 直下だけを列挙するscanner
- `.service`の正規unit ID検証
- 通常ファイル、ホーム内／外リンク、壊れたリンク、循環リンクの区別
- systemd user managerのD-Bus `LoadUnit` とunit propertiesによる読み取り照合
- load errorや照合失敗を非表示にせず、操作不能な候補として保持
- 明示登録・登録解除のapplication service
- 登録済みunit消失時のmissing表示と、再出現時の登録自動復元
- GSettings `registered-units` repository
- 登録直前の再スキャンによる古い発見結果の拒否

## 3. 安全境界

- scannerは追加の検索範囲をサービス発見には使わない。
- D-Bus adapterはフェーズ2では読み取りだけを行う。
- unit fileの解決不能、ホーム外リンク、load errorはread-onlyとなる。
- ホーム内unit fileだけではワークロード全体を安全と断定せず、参照先解析が完了するまでaccess modeをunknownとする。
- 登録は操作許可そのものではなく、利用者の管理対象選択として扱う。

ExecStart、EnvironmentFile、WorkingDirectory等を含む最終的な可操作性判定は、フェーズ3の詳細取得と統合する。したがって現段階では実サービスへの変更操作を有効にしない。

## 4. 自動テスト

2026-08-26時点で全23件が成功した。フェーズ2固有の確認には次を含む。

- 起点外を列挙しないことと決定的な並び順
- 壊れたリンクと循環リンクを候補として可視化し、安全側に倒すこと
- ホーム外リンク、load error、照合失敗をread-onlyにすること
- 登録、missing、再出現、登録解除の状態遷移
- 発見後に消失したunitを登録直前の再確認で拒否すること
- GSettingsから不正なunit IDを採用しないこと

## 5. 実機確認

`work/validation/systemd/validate-phase2-discovery.py` は、実際の発見起点とsystemd user managerを読み取る。登録確認にはメモリ内repositoryだけを使い、サービスや設定を変更しない。

期待結果は次のとおり。

- 発見件数と照合後件数が一致する
- 各候補についてload、active、access、registrationが表示される
- 候補がある場合、メモリ内での登録・登録解除確認が成功する
- 最後に成功メッセージと「サービスを変更していない」旨が表示される

### 5.1 実施結果（2026-08-26）

- 発見起点: `/home/yoshimi/.config/systemd/user`
- 発見候補: 1件
- `script-runner.service`: `load=loaded`、`active=active`、`access=unknown`、`registration=discovered`
- メモリ内の明示登録・登録解除: 成功
- start、stop、enable、disable、ファイル変更: なし

`access=unknown` は意図した安全側の結果である。フェーズ3でExecStart等の参照先を取得・評価するまでは、unit fileがホーム内にあることだけを根拠に変更操作を許可しない。

## 6. 次フェーズへの持越し

- unitのExecStart等の詳細取得
- 参照先の役割分類と信頼できるUbuntuランタイム判定の製品コード統合
- trusted user rootsの編集UIと永続化
- 発見候補・登録済み・missingを扱う一覧UI
- 変更操作直前の完全なPathAssessment再検証
