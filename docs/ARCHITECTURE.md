# アーキテクチャ設計

## 1. 方針

UI、ユースケース、systemd/journal 接続、永続化、ポリシー判定を分離する。v0.1 は `.service` のみだが、ユニット種別ごとの能力をデータとして表現し、将来の timer/socket/path と別バックエンドの cron に備える。

## 2. 論理構成

```text
GTK Presentation
    ↓ view models / commands
Application Services
    ├─ Discovery & Registration
    ├─ Status & Operations
　　├─ Unit File Editing & Validation
    └─ Log Query
    ↓ ports
Domain
    ├─ Unit, UnitState, Capability
    ├─ ManagementRegistration
    └─ AccessPolicy / PathAssessment
    ↓ adapters
Systemd User Adapter | Journal Adapter | Settings Repository | Locale Catalog
```

UI から `systemctl` や `journalctl` を直接呼ばない。systemd 接続はuser busの `org.freedesktop.systemd1` D-Bus APIを第一手段とし、CLI が必要な箇所は固定実行ファイルと引数配列で呼び出す。journalはpython-systemd adapterをワーカーで使用する。

## 3. 主要コンポーネント

| コンポーネント | 責務 |
|---|---|
| UnitDiscovery | 発見起点の列挙、systemd 認識状態との照合、リンク解決 |
| RegistrationService | 明示登録、永続化、消失ユニットの除外 |
| UnitQueryService | Description、Active、Enable、詳細の取得と正規化 |
| UnitCommandService | 能力とポリシーを再検証して操作、結果再取得 |
| PathPolicy | 全参照先を正規化し managed/read-only/unknown を判定 |
| JournalQueryService | unit 条件付き journal 読取、ページング、キャンセル |
| SettingsRepository | スキーマ付き設定、登録 ID、補助範囲の保存 |
| I18nService | locale 判定、翻訳カタログ選択 |
| UnitEditingService | 原本読込、事前検証、競合検出、保存、reload、再スキャンの統括 |
| UnitFileStore | 直接配置された通常ファイルの安全な読書きと明示バックアップ |
| UnitFileVerifier | 基本構造検査と`systemd-analyze --user verify`によるステージ済み内容の検証 |

## 4. データモデル

```text
UnitId: canonical unit name
UnitRecord:
  id, description, fragment_path, resolved_fragment_path
  active_state, sub_state, enable_state
  exec_paths[], environment_file_paths[]
  references[]: path, role, resolution_state, trust_state
  discovery_state, registration_state
  access_mode: manageable | read_only | unknown
  access_reasons[]
  capabilities[]

Settings:
  schema_version
  registered_unit_ids[]
  trusted_user_roots[]
  language_preference: system (future: ja | en)
  appearance_preference: system | light | dark
```

登録情報はパスではなく canonical unit ID を主キーとする。パスは毎回再解決し、古い判定を操作認可に利用しない。

## 5. 発見・登録フロー

1. `~/.config/systemd/user/` 直下と systemd が許す関連構造から `.service` 候補を取得する。
2. シンボリックリンクを解決し、循環・不存在・権限エラーを記録する。
3. systemd user manager に認識される canonical unit と照合する。
4. 認識される候補だけを「発見済み」として提示する。
5. ユーザーの明示操作で登録 ID を保存する。
6. 起動時・再スキャン時に登録 ID を再照合し、消失したものを `missing` として保持・通知する。
7. missing のユニットが再出現した場合は、以前の登録状態を自動復元する。登録情報の削除はユーザーの明示操作で行う。

追加の補助範囲はステップ1の発見場所には使わず、参照先の可操作性判定だけに使う。

## 6. 可操作性判定

ユニットファイルの実体、ExecStart、WorkingDirectory、明示された EnvironmentFile など、解析可能な参照先を正規化し、unit definition、system executable/runtime、user workload、configuration/data、unresolved/dynamic に分類する。

Ubuntu のパッケージ管理下にあり、root 所有かつ一般ユーザーが書換不能な `/usr/bin/python3` 等は、信頼できる system executable/runtime としてホーム外でも許容できる。user workload と configuration/data はホーム内の許可範囲にあることを要求する。分類不能、信頼性を確認できない、または動的で安全を証明できない参照は `unknown` とし、保守的に表示のみにする。

例として `ExecStart=/usr/bin/python3 /home/alice/MyApp/app.py` は、Python が信頼できるシステム実行基盤で、スクリプトと関連設定が許可範囲内なら `manageable` と判定できる。

systemd の完全な指定子・環境展開を静的に再実装しない。解析不能箇所は理由付きで unknown とする。最終判定は操作直前にも行う。

## 7. コマンドと状態同期

- 同一ユニットの変更操作は直列化する。
- 操作前に登録・存在・access mode・capability を再検証する。
- 完了後は状態を再取得し、UI の楽観的な成功表示を避ける。
- `daemon-reload` は user manager 全体への操作なので明示確認し、完了後に全体を再スキャンする。
- `daemon-reload` は個別unitのaccess modeに依存させず、現在ユーザーのuser manager以外には実行しない。
- タイムアウトとキャンセルを備え、UI スレッドを塞がない。

## 8. ログ

journal は対象 canonical unit で厳密に絞り、既定件数を限定して新しい順に取得する。追加読込と更新を別操作にし、独自永続化しない。権限不足、journal 不在、切替・ローテーションは通常の空状態またはエラーとして扱う。

user unitのmatchは、service process側の `_SYSTEMD_USER_UNIT` とuser manager側の `USER_UNIT` をORで統合し、両分岐を現在UIDで限定する。journal entryのUID、timestamp、priority、cursor、messageはadapter境界でdomain型へ正規化し、bindingが返す文字列・整数の差をUIへ漏らさない。

## 9. 永続化

XDG のユーザー設定領域を使い、原子的置換で保存する。設定には `schema_version` を持たせる。外観設定の初期値は `system` とし、GNOME/GTK が通知するシステム外観の変更へ追従する。`light` または `dark` の手動指定時はシステム設定より優先し、再起動後も保持する。登録情報はキャッシュであり権限根拠ではない。破損時は退避・初期化を案内し、外部入力として検証する。

## 10. サービスファイル作成・編集

1. 作成時はcanonical `.service` 名、編集時は発見起点直下の通常ファイルだけを受け付ける。
2. 編集時は元内容のSHA-256リビジョンを保持する。
3. UTF-8、256 KiB上限、ディレクティブ形式、`[Service]`セクションをアプリ側で検査する。
4. 隔離一時ディレクトリの同名ファイルを`systemd-analyze --user verify`で検証する。
5. 利用者に保存内容とバックアップ選択を確認する。
6. 保存直前に所有者、file type、mode、リビジョンを再検査し、同一ディレクトリ内のmode 0600一時ファイルから原子的に置換する。
7. 保存後にuser managerをreloadして再スキャンする。reload失敗時は保存済みと明示し、成功と誤認させない。
