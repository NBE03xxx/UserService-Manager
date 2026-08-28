# v0.1 リリース準備状況

## 判定

**実装受入: 条件付き合格。配布リリース: 未承認。**

フェーズ1〜6の機能実装とUbuntu 26.04 LTS上の主要実機検証は完了した。Must要件の中核挙動、ネイティブpackageのbuild/install/uninstall、縮退動作、アクセシビリティを確認できている。一般公開用v0.1としては、GitHubの公開URL確定が残っている。

## 完了した証跡

- 要件ID 39件とTEST_PLAN追跡IDが完全一致
- 自動テス50件成功
- GSettings schema strict検証成功
- desktop entry検証成功
- AppStream XML構文検証成功
- Ubuntu 26.04 LTS / GNOME / Waylandで発見、登録、状態、詳細、操作、journalを確認
- start/stop/restart、enable/disable、reloadの実機確認とfixture完全削除
- journalのUID/unit限定、ページング、上限、非永続化を確認
- 日本語・英語の主要画面、ログ画面、ライト／ダーク、スクロールを確認
- 診断情報を通常表示から分離し、明示コピーを提供
- Meson configure/build/test、gettext catalog build、一時領域へのinstall smoke testが成功
- Debian package `user-service-manager_0.1.0~dev1_all.deb`のbuildが成功
- Ubuntu 26.04 LTSで`.deb`のinstallと製品モード起動が成功
- `.deb`のuninstall/reinstallに成功し、ユーザーの登録サービスと外観設定が保持されることを確認
- Open JTalk日本語音声を使うOrcaで主要button、状態、read-only理由、確認画面を実機確認

## 未完了・リリース阻害項目

| 項目 | 関連要件 | 状態 | 解消条件 |
|---|---|---|---|
| AppStream homepage | 配布品質 | 公開先未決 | 正式URL決定後にmetadataへ追加 |
FR-015の追加管理範囲UIはShould要件であり、v0.1では既知の制約とする。policyの拡張点とGSettings schemaは用意済みで、後続フェーズで設定UIと永続化を実装する。

トップ文言は「ユーザーサービスマネージャー」と「〜ごゆっくりどうぞ〜」に確定し、英語は「User Service Manager」と「— Take your time —」とする。

## 配布準備として追加したもの

- Debian `control`、`rules`、`changelog`、copyright、source format
- Ubuntu依存を導入してunit test、metadata、Meson build/testを行うCI
- gettextが未導入でも受入用MOを生成できる検証専用compiler
- 日本語・英語を分離した通常セッション用ランチャー
- 統合受入チェックリスト

## 次の判定ゲート

1. GitHubの公開URLを確定し、AppStreamとREADMEを更新する。
2. 全Must受入項目完了後にのみv0.1リリース承認へ変更する。

## 縮退時の外観制約

通常セッションではGNOMEのlight/dark変更へ実行中に追従する。user busを完全に利用不能にした環境ではGNOMEのシステム外観情報と変更通知を取得できないため、`system`モードの正確な追従は保証しない。手動light/darkは利用可能であり、サービス操作はread-onlyへ縮退する。
