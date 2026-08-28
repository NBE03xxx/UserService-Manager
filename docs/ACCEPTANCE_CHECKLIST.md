# v0.1 統合受入チェックリスト

## 実施環境

- OS: Ubuntu 26.04 LTS
- Desktop: GNOME / Wayland
- 権限: 一般ユーザー。sudo、root、Polkit昇格を使用しない
- 対象: `systemd --user` の `.service`

実施日、GNOME版、systemd版、言語、外観モード、実施者を結果欄へ記録する。

## 安全確認

- [x] 発見起点外の孤立serviceを候補に含めない
- [x] 壊れた／循環／領域外リンクを操作可能にしない
- [x] packaged runtimeとuser workloadを分離評価する
- [x] 未登録・read-only・missingへの変更操作を拒否する
- [x] 操作直前に再スキャン・再評価する
- [x] systemd変更にshell文字列連結を使わない
- [x] journalをUIDとunitで限定し、件数・本文長を制限する
- [x] journal本文を独自保存しない
- [x] 検証unitを停止・無効化・削除して復元する

## 機能確認

- [x] 発見、登録、登録解除、再起動後の登録保持
- [x] missingと再出現
- [x] Active／Sub／UnitFileState／Description／path／ExecStart表示
- [x] 検索、実行中、停止中、表示のみフィルター
- [x] start、stop、restart、enable、disable
- [x] user manager reloadと確認画面
- [x] 操作完了後の状態再取得
- [x] journal表示、過去読込、検索、コピー、更新
- [x] ライト、ダーク、システム追従

## UI・アクセシビリティ確認

- [x] 状態を文字とアイコンで示し、色だけに依存しない
- [x] read-only／unknown理由を詳細に表示する
- [x] 影響のある操作に確認画面を表示する
- [x] icon buttonにtooltipを付ける
- [x] 長い詳細を含む画面全体を縦スクロール可能にする
- [x] ログ本文を折り返し・選択可能にする
- [x] キーボードだけで登録、詳細、操作、ログ、コピーを通し確認する
- [x] GNOMEの大きな文字設定で主要画面を確認する
- [x] Orcaで主要button、状態ラベル、read-only理由、確認画面を確認する

Ubuntu日本語環境でOpen JTalkをSpeech Dispatcherの日本語音声として使用し、Orcaによる主要操作の読み上げを確認した。

## 国際化確認

- [x] `ja_JP.UTF-8`で全主要画面が日本語になる
- [x] `C.UTF-8`で全主要画面が英語になる
- [x] 日本語・英語で切れ、重なり、操作不能がない
- [x] source文字列と日本語catalogの一対一対応
- [x] format placeholderの一致
- [x] GNU MOへのcompileと代表翻訳の読込

## エラー・縮退確認

- [x] load errorを候補として表示し変更操作を無効化する
- [x] 操作失敗をクラッシュさせず通知する
- [x] 読込失敗に再試行と診断コピーを表示する
- [x] journal空状態と読込失敗状態を表示する
- [x] user busを利用不能にした対象環境試験
- [x] journalを利用不能にした対象環境試験

## 配布確認

- [x] GSettings schemaのstrict検証
- [x] desktop entry検証
- [x] AppStream XMLの構文検証
- [x] Meson configure/build/test/install smoke test
- [x] gettext標準toolchainによるcatalog build
- [x] AppStreamの公開homepage URL設定
- [x] `.deb` buildとUbuntu 26.04環境でのinstall/uninstall/reinstall試験

`.deb`削除後にアプリ本体が削除され、再インストール後に登録サービスと外観設定が保持されることを確認した。

## 判定規則

Must要件に関係する未完了項目がある間はリリース不可とする。開発用runtimeが未導入、公開URLが未決、または対象環境の縮退試験が未完了の場合、実装完了とリリース可能を区別して記録する。

トップは「ユーザーサービスマネージャー」、副題は「〜ごゆっくりどうぞ〜」に確定した。英語は「User Service Manager」と「— Take your time —」とする。

ヒーロー画像は、受け皿付きコーヒーカップの線画アイコンを96px相当で表示する最終案を実画面で確認した。

通常セッションでは、GNOMEのシステム外観を変更するとアプリが再起動なしで追従することを確認した。user busを意図的に切断した縮退状態ではシステム外観情報・変更通知を取得できないため、`system`は追従不能となるが、手動light/darkは利用できる。この制約は縮退時だけの既知事項とする。
