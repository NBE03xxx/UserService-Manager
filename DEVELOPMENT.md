# 開発ガイド

## 現在の段階

v0.2（作成・編集の安全基盤）は製品版v1.2.0として実装・受入済みです。v1.1.0は欠番であり、版番として再利用しません。

ソースからの開発起動は安全なmock backendを使用します。`USM_BACKEND=systemd`で実状態とjournalの読み取りを接続し、変更操作はさらに`USM_COMMANDS=enabled`を明示した場合だけ接続されます。インストール済みの`user-service-manager`ランチャーは製品用として両方を有効にしますが、すべての変更操作に登録・path policy・操作直前再評価の安全ゲートが適用されます。

## Ubuntu 26.04で想定する開発依存

```text
python3
python3-gi
gir1.2-gtk-4.0
gir1.2-adw-1
python3-systemd
meson
gettext
pkg-config
desktop-file-utils
appstream
```

Meson、gettext、pkg-config等を使ったネイティブbuildはUbuntu 26.04 LTSで検証済みです。

## 依存を追加しない中核テスト

プロジェクトルートで実行します。

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

## データ検証

```bash
glib-compile-schemas --strict --dry-run data
desktop-file-validate data/io.github.NBE03xxx.UserServiceManager.desktop
appstreamcli validate --no-net data/io.github.NBE03xxx.UserServiceManager.metainfo.xml
```

AppStreamのhomepageは `https://github.com/NBE03xxx/UserService-Manager` です。

## 手動UI検証

schemaをプロジェクト内でcompileし、通常セッションから起動します。

```bash
glib-compile-schemas --strict data
GSETTINGS_SCHEMA_DIR="$PWD/data" PYTHONPATH="$PWD/src" python3 -m user_service_manager.main
```

通常起動ではmockデータだけを表示します。実サービスの読み取りUIは`work/validation/ui/run-phase3-app.sh`、使い捨てunitに限定した変更操作UIは`work/validation/ui/run-phase4-app.sh`、journal UIは`work/validation/ui/run-phase5-app.sh`で検証できます。ネットワーク通信は行いません。
