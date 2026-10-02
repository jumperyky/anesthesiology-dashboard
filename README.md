# Anesthesiology Update Dashboard

麻酔科医（特に臨床復帰者）向けの、最新臨床トレンド論文自動収集・要約・通知システムです。
毎朝6時（JST）にPubMedからガイドラインや重要論文を自動収集し、Geminiで要約してLINEに通知＆ダッシュボード更新を行います。

## Features
- **Smart Fetching**: PubMed APIを使用し、過去1年のガイドライン・コンセンサス・システマティックレビュー・メタ解析を新しい順に検索。対象は麻酔科のコア誌に載ったものと、題名に麻酔の語がある他誌の論文。既読論文は自動で重複排除。
- **AI Summarization**: Gemini 2.5 Flash を使用し、指導医視線で「臨床アクション」を中心に要約。
- **Notifications**: LINE Messaging API（ブロードキャスト）で、その日のピックアップをお知らせ。
- **Dashboard**: Streamlit製の見やすいスマホ対応UI。

## Setup

### Prerequisites
- Python 3.10+
- PubMed (Entrez) 用のメールアドレス
- Google Gemini API Key
- LINE Messaging API Channel Access Token (LINE Developers)

### Installation
1. Clone the repository
   ```bash
   git clone <repository-url>
   cd Anesthesiology_dashboard
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment Variables
   Create a `.env` file in the root directory:
   ```ini
   EMAIL=your_email@example.com
   GEMINI_API_KEY=your_gemini_api_key
   LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
   ```

## Usage

### Run Batch (Fetch & Summarize)
手動でデータを更新する場合に使用します。
```bash
python run_batch.py
```
実行すると `data/papers.json` が更新され、LINEに通知が飛びます。

### Run Dashboard
ダッシュボードをローカルで起動します。
```bash
streamlit run app.py
```

## Deployment

### 1. GitHub Actions (Auto Update)
このリポジトリには、毎日 6:00（JST）に `run_batch.py` を実行して `data/` をコミットするワークフロー（`daily_update.yml`）が含まれています。

GitHubのリポジトリ設定 (Settings > Secrets and variables > Actions) に以下のRepository secretsを追加してください:
- `EMAIL`
- `GEMINI_API_KEY`
- `LINE_CHANNEL_ACCESS_TOKEN`

### 2. Streamlit Community Cloud (Hosting)
1. [Streamlit Community Cloud](https://streamlit.io/cloud) にサインイン。
2. "New app" をクリックし、このGitHubリポジトリを選択。
3. "Main file path" に `app.py` を指定。
4. "Deploy!" をクリック。

これで、`data/papers.json` がGitHub Actionsによって更新されるたびに、Streamlitアプリも（必要に応じて再起動やリロードで）最新情報を表示します。

## Directory Structure
```
.
├── .github/workflows/ # GitHub Actions config
├── data/              # Data storage (JSON)
├── src/               # Source code
│   ├── fetcher.py     # PubMed API interaction
│   ├── summarizer.py  # AI summarization
│   ├── notifier.py    # LINE notification
│   └── utils.py       # Utilities
├── app.py             # Streamlit Dashboard info
├── run_batch.py       # Batch entry point
└── requirements.txt
```
