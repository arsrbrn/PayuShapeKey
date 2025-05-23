# Payu Morph

BlenderでMMDモデルのシェイプキー（モーフ）を効率的に管理するためのアドオンです。

<img width="240" alt="image" src="https://github.com/user-attachments/assets/c39d6cfd-e399-40eb-93c8-72eec28491f3" />




## 💫 こんな時に便利！

例）顔とアイラインを別オブジェクトに分けている場合：

1. 「全シェイプキーを左右分割」を「アイライン」で実行
2. 「顔」にも実行（口の分割など必要ないモーフは削除）
3. 「全シェイプキーにドライバーを追加」を「アイライン」選択中に実行
4. 　完成！アイラインは左右に分割され、ウィンクも自動搭載。シェイプキーを動かすと顔も一緒に動きます

## ✨ 主な機能

<img width="227" alt="image" src="https://github.com/user-attachments/assets/f35e266b-9932-4a31-9be5-e5fe8699ea63" />


### 🔄 シェイプキーの左右分割
- **単一のシェイプキー分割**
  - 元のシェイプキーを残したまま、新たに分割されたシェイプを作成
  - 自動で「〇〇左」「〇〇右」という名前に設定
- **全シェイプキーの一括分割**
  - まばたき→ウィンク2/ｳｨﾝｸ2右、笑い→ウィンク/ウィンク右に自動変換
  - 既に分割済みのシェイプキーは自動スキップ
- **ミラーモディファイア対応**
  - ミラーモディファイアがあっても自動で適用
  - Auto Mirror（アドオン）で再ミラー＆一括統合で実行前を再現できます

### 🎯 シェイプキーの統合
- **左右シェイプキーの統合**
  - 同名シェイプキーがある場合は既存を保持
- **全シェイプキーの一括統合**
  - 整理整頓に便利！また分割したい時は全分割で一発対応
- **MMD用名前マッピング**
  - ウィンク系を自動で「笑い」に、ウィンク2系を「まばたき」に統合

### 🔗 ドライバー設定
- **選択シェイプキーのドライバー追加**
  - 顔とアイラインの別オブジェクト連動に最適
- **全シェイプキーの一括ドライバー設定**
  - 分割後の一括設定で作業効率アップ
- **ドライバー削除機能**
  - 個別調整したい時に便利です

### 🎭 MMD対応
- **シェイプキー名のMMD形式への変換**
  - 「まばたき左/右」「笑い左/右」をMMD用に自動変換
  - 個別分割後の整理に使用してください

## 📥 インストール方法

1. このリポジトリの[Releases](../../releases)から最新のZIPファイルをダウンロード
2. Blenderを起動し、`編集 > プリファレンス > アドオン`を開く
3. `ファイルからインストール`をクリックしてダウンロードしたZIPファイルを選択
4. アドオンのチェックボックスをオンにして有効化

## 🎮 使い方

### 基本操作
1. プロパティパネルの「データ」タブを開く
2. 「Payu Morph」セクションで各機能を利用可能
   - シェイプキーパネルの真上に配置すると使いやすいです
   - 邪魔な時は折りたたみ可能

### シェイプキーの分割
1. 分割したいシェイプキーを選択
2. `分割`ボタンをクリック
3. 選択したシェイプキーが左右に分割されます

### シェイプキーの統合
1. 統合したい左右のシェイプキーの片方を選択
2. `マージ`ボタンをクリック
3. 左右のシェイプキーが1つに統合されます

### ドライバー設定
1. ドライバーを設定したいシェイプキーを選択
2. `ドライバーを追加`ボタンをクリック
3. 同名のシェイプキーを持つ他のオブジェクトにドライバーが設定されます

### 便利な機能
- シェイプキーの右クリックメニューから一括処理が可能
- プログレスバーで処理状況を確認可能
- エラー発生時は詳細なメッセージを表示

## ⚠️ 注意事項

- 処理前にデータのバックアップを推奨します
- ミラーモディファイアの適用は元に戻せません
- MMD用の名前変換は特定のパターンのみ対応

## 🔧 動作環境

- Blender 2.80以降
- Windows / Mac / Linux

## 🐛 バグ報告・機能要望

[Issues](../../issues)にて受け付けています。

## 📝 ライセンス

[MITライセンス](./LICENSE)の下で公開されています。

## 🙏 謝辞

このアドオンの開発にあたり、以下に感謝いたします：

- コード生成に協力してくれた Claude (Anthropic)
