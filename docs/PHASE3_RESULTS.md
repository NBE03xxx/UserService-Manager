# フェーズ3 実装・検証結果

## 1. 状態

状態・詳細取得、参照先の安全性判定、実サービス一覧UI、検索・絞り込み、登録操作の画面統合を実装し、2026-08-26にUbuntu 26.04 LTS / GNOME / Waylandで確認した。フェーズ3は完了とする。start、stop、restart、enable、disable等の変更操作はまだ接続していない。

## 2. 実装内容

- systemd user managerからDescription、LoadState、ActiveState、SubState、UnitFileState、FragmentPathを取得
- service interfaceからExecStart、WorkingDirectory、EnvironmentFilesを取得
- 取得処理を作業スレッドで行いGTKのメインループを停止させない
- unit file、runtime、ワークロード、作業ディレクトリ、環境ファイルを安全性判定
- root所有、一般ユーザー書換不能、dpkg管理下のsystem runtimeを許可
- ホーム内のユーザーワークロードと設定を許可
- 動的、解決不能、領域外の参照をunknownまたはread-onlyに制限
- WorkingDirectoryを基準に相対ExecStartパスを評価
- 実サービスの一覧、展開式詳細、状態、可操作性、判定理由を表示
- 発見候補の管理対象への追加と登録解除
- テキスト検索、全て／実行中／停止中／表示のみの絞り込み
- 再スキャン、読込中、空、失敗状態

## 3. 検証結果

自動テスト全33件が成功した。信頼できるPythonとホーム内スクリプト、外部・動的参照、EnvironmentFile、WorkingDirectory、相対パス、検索と各フィルターを含む。

実機の`script-runner.service`は`loaded`、`active`、`manageable`となった。venvのPython実体、相対指定の`app/main.py`、WorkingDirectory、EnvironmentFileを個別に評価できた。読み取り検証ではサービス・設定を変更していない。

GUIでは実サービス1件、読込完了、Add／Remove、再スキャン、検索、絞り込み、隔離したGSettingsへの登録永続化、ライト／ダーク表示を確認した。

初回確認では更新時に古い行とspinnerが残る問題が見つかった。アプリが追加した行を明示追跡して削除する方式へ修正し、再確認で解消した。再スキャンは候補1件では非常に短く、spinnerを目視できないが正常に完了する。

## 4. 安全上の結論

`ExecStart=/home/yoshimi/ScriptRunner/venv/bin/python app/main.py`のような構成では、venvのリンク先runtime、相対スクリプト、WorkingDirectory、EnvironmentFileを個別評価したうえでのみmanageableになる。unit fileがホーム内にあることだけを根拠にはしない。

## 5. 次フェーズ

フェーズ4で変更操作adapterとUIを実装する。各操作の直前に登録、存在、最新PathAssessment、capabilityを再検証し、完了後に状態を再取得する。安全ゲートが完成するまで操作を露出しない。
