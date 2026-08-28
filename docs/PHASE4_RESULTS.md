# フェーズ4 実装・検証結果

## 1. 状態

変更操作adapter、安全ゲート、操作UI、確認画面、多重実行防止、完了後再取得を実装し、2026-08-26にUbuntu 26.04 LTS / GNOME / Waylandで検証した。検証unitの復元と削除まで完了したため、フェーズ4は完了とする。

## 2. 実装内容

- user busのsystemd Managerに対するStartUnit、StopUnit、RestartUnit
- EnableUnitFiles、DisableUnitFilesと、その直後のManager.Reload
- 明示的なuser manager Reload
- JobRemovedを待ち、`done`以外とtimeoutを失敗として扱う処理
- 操作直前の全体再スキャンとPathAssessment再評価
- 登録済み、loaded、manageable、capability保有の全条件確認
- unit単位の多重操作拒否とreloadの多重実行拒否
- 操作完了後の状態再取得
- 管理可能かつ登録済みunitだけに操作UIを表示
- Stop、Restart、Disable、Reloadの確認画面
- 完了・失敗通知

## 3. 自動テスト

全39件が成功した。フェーズ4固有の試験には次を含む。

- 操作前再検証と操作後再取得
- 未登録、read-only、非変更capabilityの拒否
- 同一unitへの並行操作拒否
- reload後の再取得
- enable/disable後にManager.Reloadを必ず呼ぶこと

## 4. 実機検証

### 4.1 安全ゲート

`codex-usm-validation-basic.service`は`/usr/bin/sleep`が現環境のruntime信頼条件を満たさずread-onlyとなり、操作前に拒否された。サービス変更は行われなかった。この結果により、不明なruntimeを安易に許可しないfail-closed動作を確認した。

### 4.2 製品コード経由の操作

管理可能と判定された`codex-usm-validation-python.service`だけを対象とし、次を確認した。

- 初期状態: inactive / disabled
- start後: active
- stop後: inactive
- enable後: enabled
- user manager reload後: enabledを維持
- disable後: disabled
- 最終状態とcleanup: inactive / disabled

最初の試行ではDisableUnitFiles直後のUnitFileStateがmanager cache上でenabledのままだった。製品adapterを修正し、enable/disableのリンク変更直後にManager.Reloadしてから状態を再取得することで解消した。

### 4.3 GUI

- 検証用設定で明示登録したmanageable unitだけに操作ボタンを表示
- Start、Stop、Restart、Enable、Disableが正常動作
- 破壊的操作の確認画面が表示
- 実行後の状態が保持・再表示される
- user manager reloadが確認画面経由で動作

初回は操作欄が展開詳細の最下部にあり見つけにくかった。操作欄を展開直後の先頭へ移動した。

## 5. 後片付け

検証unitは停止・無効状態へ戻した後、`~/.config/systemd/user/`からすべて削除し、daemon-reloadとfailed stateのresetを実施した。既存の`script-runner.service`は操作・削除していない。

## 6. 次フェーズ

フェーズ5でjournalの対象unit限定読取、件数上限、更新、空・失敗状態、表示とコピーを実装する。ログをアプリ独自には保存しない。
