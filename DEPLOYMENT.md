# AIマラソンコーチ 公開手順書

## 📋 概要

このドキュメントでは、AIマラソンコーチをWebアプリとして公開する手順を説明します。

最も簡単な方法は **Streamlit Community Cloud**（無料）を使用することです。

---

## 🚀 Streamlit Cloudでの公開

### 前提条件
- GitHubアカウント
- Gemini APIキー

### Step 1: GitHubリポジトリの準備

1. `.gitignore`に以下が含まれていることを確認：
   ```
   .streamlit/secrets.toml
   __pycache__/
   *.pyc
   .DS_Store
   ```

2. GitHubにプッシュ：
   ```bash
   cd /Users/yasuchin/apps/ai-marathon-coach/ai-marathon-coach
   git add -A
   git commit -m "Ready for deployment"
   git push origin main
   ```

### Step 2: Streamlit Community Cloudにサインアップ

1. [share.streamlit.io](https://share.streamlit.io/) にアクセス
2. 「Continue with GitHub」でサインイン
3. GitHubアカウントを連携

### Step 3: アプリをデプロイ

1. 「New app」をクリック
2. 以下を設定：
   - **Repository**: `AkiRun-Lab/ai-marathon-coach`（あなたのリポジトリ）
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. 「Deploy!」をクリック

### Step 4: Secretsの設定（重要）

**APIキーは絶対にコードに直接書かないでください！**

1. デプロイ設定画面で「Advanced settings」をクリック
2. 「Secrets」タブを開く
3. 以下を入力：
   ```toml
   GEMINI_API_KEY = "あなたのGemini APIキー"
   ```
4. 「Save」をクリック

または、デプロイ後に設定する場合：
1. アプリのダッシュボードを開く
2. 右上の「⋮」→「Settings」→「Secrets」
3. 上記と同じ内容を入力して保存

---

## ⚙️ 現在のAPIキー読み込み方法

現在のコードはすでにStreamlit Cloudに対応しています：

```python
# src/ai/gemini_client.py
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
```

この設定により：
- **ローカル開発**: `.streamlit/secrets.toml`から読み込み
- **Streamlit Cloud**: ダッシュボードのSecretsから読み込み

---

## 🔗 公開後のURL

デプロイ完了後、以下のようなURLでアクセスできます：
```
https://ai-marathon-coach.streamlit.app/
```

カスタムURLも設定可能です。

---

## ⚠️ 注意事項

### 無料プランの制限
- **リソース**: 限定的なCPU/メモリ
- **スリープ**: 一定時間アクセスがないとスリープ（初回アクセスに時間がかかる）
- **同時接続**: 制限あり

### セキュリティ
- APIキーは必ずSecretsで管理（コードにハードコードしない）
- `.streamlit/secrets.toml`はGitにプッシュしない

### 費用
- **Streamlit Cloud**: 無料（Community Plan）
- **Gemini API**: 使用量に応じた課金（無料枠あり）

---

## 🔧 トラブルシューティング

| 問題 | 解決方法 |
|:-----|:-----|
| デプロイ失敗 | ログを確認し、依存関係をrequirements.txtに追加 |
| APIエラー | SecretsにGEMINI_API_KEYが正しく設定されているか確認 |
| 表示崩れ | ブラウザキャッシュをクリア |

---

## 📚 参考リンク

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Google AI Studio（APIキー取得）](https://aistudio.google.com/apikey)

---

*AIマラソンコーチ v1.0.0*
