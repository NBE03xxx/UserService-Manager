# User Service Manager — 設計文書

Ubuntu/GNOME/Wayland 上で、一般ユーザーが `systemd --user` のユーザーサービスを安全に確認・編集・操作するための GTK/libadwaita GUI アプリケーションです。第一検証環境は Ubuntu 26.04 LTS です。

- GitHub: https://github.com/NBE03xxx/UserService-Manager
- License: [MIT](LICENSE)

## v1.2.0 の機能範囲

- 対象ユニット: `.service` のみ
- 発見起点: `~/.config/systemd/user/`
- 管理方法: 発見したサービスをユーザーが明示的に管理対象へ登録
- 主機能: 一覧、状態確認、start/stop/restart、enable/disable、status、daemon-reload、journal ログ表示
- ファイル: `.service` の新規作成、元ファイル編集、systemd事前検証、明示選択によるバックアップ
- 権限: 一般ユーザー権限のみ（`sudo`、Polkit による昇格なし）
- UI: GTK 系、GNOME/Wayland を優先
- 言語: locale により日本語/英語を自動選択
- 外観: 初期状態ではシステム設定に従い、ライト／ダークを手動選択可能

ユーザー領域外を参照するサービスは、状態・詳細・ログのみ閲覧可能です。状態変更ボタンは無効化します。ファイル編集は発見起点に直接配置された安全な通常ファイルに限定し、symlink、削除、drop-in管理は対象外です。

ただし、Ubuntu が提供・管理する `/usr/bin/python3` 等の信頼できるシステム実行基盤は、単にホーム外にあるという理由だけでは表示専用にしません。実際のユーザーワークロードや設定ファイルの所在を区別して判定します。

## 文書一覧

| 文書 | 内容 |
|---|---|
| [REQUIREMENTS.md](docs/REQUIREMENTS.md) | 一意な ID を付けた検証可能な要件 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 構成、データフロー、境界、データモデル |
| [UI_DESIGN.md](docs/UI_DESIGN.md) | 画面、状態、操作フロー、アクセシビリティ |
| [SECURITY.md](docs/SECURITY.md) | 脅威モデル、安全性判定、操作制限 |
| [I18N.md](docs/I18N.md) | 日本語・英語対応方針 |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | テスト方針、テストケース、要件追跡表 |
| [ROADMAP.md](docs/ROADMAP.md) | v0.1 と後続段階の境界 |
| [DECISIONS.md](docs/DECISIONS.md) | 主要な設計判断と未決事項 |
| [DESIGN_REVIEW.md](docs/DESIGN_REVIEW.md) | 実装前レビュー、指摘、要確認事項 |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | v0.1要件を実現した段階的な実装計画と記録 |
| [TECHNICAL_SPIKE.md](docs/TECHNICAL_SPIKE.md) | Ubuntu 26.04での技術調査と採用判断 |
| [VALIDATION_PLAN.md](docs/VALIDATION_PLAN.md) | 製品実装前の安全な実機検証計画 |
| [VALIDATION_RESULTS.md](docs/VALIDATION_RESULTS.md) | 実機検証の結果と残課題 |
| [PHASE1_RESULTS.md](docs/PHASE1_RESULTS.md) | プロジェクト基盤の実装・検証結果 |
| [PHASE2_RESULTS.md](docs/PHASE2_RESULTS.md) | 発見・登録・missing保持の実装・検証結果 |
| [PHASE3_RESULTS.md](docs/PHASE3_RESULTS.md) | 状態・詳細・安全性判定・実サービスUIの結果 |
| [PHASE4_RESULTS.md](docs/PHASE4_RESULTS.md) | 安全な変更操作と操作UIの実装・検証結果 |
| [PHASE5_RESULTS.md](docs/PHASE5_RESULTS.md) | journal限定取得とログUIの実装・検証結果 |
| [PHASE6_RESULTS.md](docs/PHASE6_RESULTS.md) | 統合受入、ビルド、リリース監査の結果 |
| [ACCEPTANCE_CHECKLIST.md](docs/ACCEPTANCE_CHECKLIST.md) | v0.1統合受入項目と実施状況 |
| [RELEASE_READINESS.md](docs/RELEASE_READINESS.md) | リリース判定、完了証跡、残課題 |
| [V0_2_RESULTS.md](docs/V0_2_RESULTS.md) | v0.2の作成・編集機能とv1.2.0受入の結果 |

開発者向けの現在の実行・検証方法は [DEVELOPMENT.md](DEVELOPMENT.md) を参照してください。

## 現在の実装状態

従来の閲覧・操作機能に加え、v0.2の作成・編集の安全基盤をv1.2.0として実装しました。v1.1.0は誤用のため欠番とし、再利用しません。

文書内の v0.1〜v0.4 は機能範囲のロードマップ番号です。v0.1の範囲は製品版 v1.0.0、v0.2の範囲はv1.2.0に対応します。

## インストール

[GitHub Releases](https://github.com/NBE03xxx/UserService-Manager/releases/latest) から `user-service-manager_1.2.0_all.deb` をダウンロードし、ファイルのあるディレクトリで次を実行します。

```bash
sudo apt install ./user-service-manager_1.2.0_all.deb
```

インストール後はGNOMEのアプリ一覧から「ユーザーサービスマネージャー」を起動できます。アンインストールは次のコマンドで行います。

```bash
sudo apt remove user-service-manager
```

## 安全な配置について

本アプリがサービスファイルを発見する場所は、原則として `~/.config/systemd/user/` だけです。ホームディレクトリ全体から `.service` を無差別に探しません。ユーザーが追加する検索範囲は、ユニットが参照する実行ファイルや設定ファイルを「管理可能なユーザー領域」と判定する補助範囲であり、サービスファイルの追加発見場所ではありません。

予測可能で安全な管理のため、関連ファイルは所有者と用途が明確なユーザーディレクトリにまとめてください。`/tmp`、用途不明の隠しディレクトリ、他アプリの内部データ領域などへの配置は推奨しません。

## 文書の検証方法

`docs/REQUIREMENTS.md` の各要件 ID を基準とし、`docs/TEST_PLAN.md` の追跡表で対応するテストケースを確認します。仕様変更時は、要件、設計、テスト、ロードマップを同じ変更で更新します。
