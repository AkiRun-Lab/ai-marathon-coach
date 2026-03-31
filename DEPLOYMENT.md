# マラソントレーニング・プランナー 公開手順書

## 📋 概要

このドキュメントでは、マラソントレーニング・プランナーをWebアプリとして公開・更新する手順を説明します。

| 項目 | 内容 |
|:-----|:-----|
| ホスティング | Streamlit Community Cloud（無料） |
| リポジトリ | https://github.com/AkiRun-Lab/ai-marathon-coach |
| 公開URL | https://ai-marathon-coach.streamlit.app/ |

---

## 🔄 既存アプリの更新手順

### Step 1: ローカルで変更をコミット

```bash
cd /Users/yasuchin/akirun_project/apps/amc
git add -A
git commit -m "更新内容の説明"
```

### Step 2: GitHubにプッシュ

```bash
git push origin main
```

### Step 3: 自動デプロイ

GitHubにプッシュすると、**Streamlit Cloudが自動的にリデプロイ**します（通常1〜2分）。

### 手動リデプロイが必要な場合

1. [share.streamlit.io](https://share.streamlit.io/) のダッシュボードにアクセス
2. アプリの「⋮」→「Reboot app」をクリック

---

## 🔐 Secrets（APIキー）の管理

### ⚠️ 重要：セキュリティ

**APIキーは絶対にコードに直接書かないでください！**

### ローカル開発での設定

`.streamlit/secrets.toml`に保存（Git管理外）：

```toml
GEMINI_API_KEY = "あなたのGemini APIキー"
```

### Streamlit Cloudでの設定

1. [share.streamlit.io](https://share.streamlit.io/) のダッシュボードにアクセス
2. アプリの「⋮」→「Settings」→「Secrets」
3. 以下を入力して保存：

```toml
GEMINI_API_KEY = "あなたのGemini APIキー"
```

### APIキー読み込みの仕組み

現在のコードはすでに対応済みです：

```python
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
```

---

## 📁 Git管理から除外されるファイル

`.gitignore`で以下が除外されています：

```
.streamlit/secrets.toml    # APIキー
__pycache__/               # Pythonキャッシュ
*.pyc                      # コンパイル済みファイル
.DS_Store                  # macOSメタデータ
```

確認コマンド：
```bash
git check-ignore -v .streamlit/secrets.toml
# 出力: .gitignore:34:.streamlit/secrets.toml
```

---

## 🚀 新規デプロイ手順（参考）

### Step 1: Streamlit Community Cloudにサインアップ

1. [share.streamlit.io](https://share.streamlit.io/) にアクセス
2. 「Continue with GitHub」でサインイン

### Step 2: アプリをデプロイ

1. 「New app」をクリック
2. 以下を設定：
   - **Repository**: `AkiRun-Lab/ai-marathon-coach`
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. 「Advanced settings」→「Secrets」でAPIキーを設定
4. 「Deploy!」をクリック

---

## ⚠️ 注意事項

### VDOTデータの編集ルール

VDOTデータ（`vdot_list.csv`, `vdot_pace.csv`）は `data/vdot/` が正規ソースです。`apps/amc/data/` 内のファイルを直接編集しないでください。

```bash
# 1. 正規データを編集
#    data/vdot/vdot_list.csv または data/vdot/vdot_pace.csv

# 2. 各アプリに同期
./scripts/sync-vdot-data.sh

# 3. 差分チェックのみ（変更なし）
./scripts/sync-vdot-data.sh --check
```

同期先: AMC（`apps/amc/data/`）、MSS（`apps/mss/data/`）、VDOT計算機（ビルド時に参照）

### 無料プランの制限
| 項目 | 制限 |
|:-----|:-----|
| リソース | 限定的なCPU/メモリ |
| スリープ | 一定時間アクセスがないとスリープ |
| 同時接続 | 制限あり |

### 費用
| サービス | 費用 |
|:---------|:-----|
| Streamlit Cloud | 無料（Community Plan） |
| Gemini API | 使用量に応じた課金（無料枠あり） |

---

## 🔧 トラブルシューティング

| 問題 | 解決方法 |
|:-----|:-----|
| デプロイ失敗 | Streamlitのログを確認、requirements.txtを確認 |
| APIエラー | SecretsにGEMINI_API_KEYが正しく設定されているか確認 |
| 自動デプロイされない | 手動で「Reboot app」を実行 |
| 依存関係エラー | requirements.txtに不足パッケージを追加 |

---

## 📚 参考リンク

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Google AI Studio（APIキー取得）](https://aistudio.google.com/apikey)
- [GitHub Repository](https://github.com/AkiRun-Lab/ai-marathon-coach)

---

*マラソントレーニング・プランナー v1.0.0*
