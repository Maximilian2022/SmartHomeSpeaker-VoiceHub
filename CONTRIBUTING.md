# コントリビューションガイド (Contributing Guide)

「Smart Home Speaker Voice Hub」への貢献にご関心をお持ちいただきありがとうございます！
バグ報告、新機能の提案、ドキュメントの改善、プルリクエストなど、あらゆる形の貢献を心より歓迎いたします。

---

## 1. 質問やアイデアのディスカッション

「こんな機能があったら便利かも」「使い方がよく分からない」「この連携はどう実装すべき？」といった相談や質問は、お気軽に **[GitHub Discussions](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/discussions)** へお寄せください。

Issue を立てる前の壁打ちや、他のユーザーとの情報交換の場としてもご活用いただけます。

---

## 2. バグ報告と機能リクエスト (Issues)

不具合の報告や具体的な機能追加の要望は、[GitHub Issues](https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/issues) から受け付けています。

- **バグ報告**: 発生した現象、再現手順、期待した動作、環境（Docker / OS / 接続スピーカーの種類）、および関連するログ（個人情報・認証トークンは必ず伏せてください）を記載してください。
- **機能リクエスト**: どのような課題を解決したいか、提案する機能のユースケースを記載していただけると検討がスムーズになります。

※セキュリティ上の脆弱性に関しては、公開 Issue ではなく [SECURITY.md](SECURITY.md) に記載の手順（非公開報告）でご連絡をお願いいたします。

---

## 3. 開発方針・アーキテクチャ規約

本プロジェクトでコードを修正・追加する際は、以下の設計方針を遵守してください。

1. **バックエンドは Python ファースト**:
   - 本プロジェクトは Node.js から Python 3.12+ (FastAPI) へ全面移行しました。
   - バックエンドのロジックや新機能は、理由がない限り Python で作成してください。
2. **フロントエンドは Vanilla JS / CSS**:
   - WebUI（`public/` 配下）は、追加のビルドツールやバンドラーを必要としない Vanilla JavaScript / Vanilla CSS を採用しています。
   - 軽量性・可読性を維持するため、重量級フレームワークの導入は避けてください。
3. **Homebridge プラグイン**:
   - `plugins/homebridge-voicehub/` は TypeScript で書かれており、Node.js 環境で動作します。修正時は `npm run build` でコンパイルして `dist/` が正しく生成されることを確認してください。
4. **設定と環境変数**:
   - 環境変数の定義や読み込みは `pydantic-settings`（`app/core/config.py`）に集約し、`.my.env.sample` にもサンプルの記載を追加してください。

---

## 4. ローカル開発環境のセットアップ

### Docker を利用する場合 (推奨)
```bash
# 1. リポジトリのクローン
git clone https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub.git
cd SmartHomeSpeaker-VoiceHub

# 2. 設定ファイルの準備
cp .my.env.sample .my.env

# 3. コンテナのビルドと起動
docker compose up --build
```
ブラウザで `http://localhost:8080` を開いて動作を確認します。

### ローカル Python 環境で動かす場合
```bash
# 仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt

# サーバーの起動
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 5. テストの実行

変更を加えた後は、必ず既存の単体テスト・スモークテストを実行し、すべてのテストが合格することを確認してください。

```bash
# テストの実行
python3 -m unittest discover -s tests -p "test_*.py"

# または特定のスモークテストの実行
python3 -m unittest tests/test_smoke.py
```

新機能やバグ修正を行う場合は、可能な限り `tests/` 配下にテストケースを追加してください。

---

## 6. プルリクエスト (Pull Request) の流れ

1. 本リポジトリを Fork し、作業用のフィーチャーブランチ（例: `feature/cool-new-feature` や `fix/issue-123`）を作成します。
2. コミットメッセージは分かりやすく記述してください（[Conventional Commits](https://www.conventionalcommits.org/) の形式 `feat:`, `fix:`, `docs:`, `refactor:` などを推奨します）。
3. テストを実行し、パスすることを確認します。
4. Fork 元の `main` ブランチに対して Pull Request を作成してください。
5. PR の説明文に、変更内容の概要と関連する Issue 番号を記載してください。

---

## 7. ライセンスへの同意

本リポジトリへのすべてのコントリビューション（プルリクエスト等）は、本プロジェクトの [MIT License](LICENSE) のもとで提供されることに同意したものとみなされます。
