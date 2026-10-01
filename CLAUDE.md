# CLAUDE.md

麻酔科の最新論文を PubMed から集め、Gemini で要約し、LINE に通知して Streamlit のダッシュボードに出す。
セットアップと使い方は [README.md](./README.md)。

リポジトリは**公開**で、GitHub Actions が毎日動いている。

## 動かす

```bash
pip install -r requirements.txt
python run_batch.py       # 取得 → 要約 → data/ 更新 → LINE 通知
streamlit run app.py      # ダッシュボード
```

`run_batch.py` をローカルで走らせると、実際に LINE のブロードキャストが全員に飛ぶ。
確認だけなら `.env` の `LINE_CHANNEL_ACCESS_TOKEN` を空にする（未設定なら通知をスキップする）。

## 構成

- `src/fetcher.py` — PubMed（Entrez）の検索と重複排除
- `src/summarizer.py` — Gemini での要約。モデル名はここに直書き
- `src/notifier.py` — LINE Messaging API のブロードキャスト。ダッシュボードの URL もここ
- `data/papers.json` / `data/processed_ids.json` — 収集結果と処理済み ID。**Actions が自動でコミットする**
- `.github/workflows/` — `daily_update.yml`（毎日 6:00 JST）と `weekly_digest.yml`（月曜 8:00 JST）

## 守ること

- **作業の前に必ず `git pull`。** `data/` は毎日ボットがコミットするので、ローカルはすぐ遅れる。
  `data/*.json` を手元で編集してコミットしない（ボットの更新と衝突する）。
- **秘密情報は `.env` と GitHub の Repository secrets だけ。** 公開リポジトリなので、
  キー・トークン・個人のメールアドレスをコード・ログ・コミットに入れない。
- ワークフローの変更は、稼働中の自動更新の挙動を変える。push する前に相談する。
- Gemini のモデル名を変えるときは、そのモデルが使えることを先に確かめる（`check_models.py`）。
- 要約のプロンプトは「復帰する同僚に指導医が紹介する」設定。臨床アクションを中心に書かせる方針を変えない。

## 既知の事情

- `weekly_digest.yml` のコミット手順に `git diff --start-number 1` という無効なオプションがあり、
  変更が無い週はジョブが失敗する。修正案はローカルの `local-wip-2026-02` ブランチにある（未 push）。
- 2026-02 時点のローカル作業（fetch ロジックの修正、デバッグ用スクリプト）は `local-wip-2026-02` に退避してある。
