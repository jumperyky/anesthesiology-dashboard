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
- `.github/workflows/daily_update.yml` — 毎日 6:00 JST に `run_batch.py` を実行して `data/` をコミットする

## 守ること

- **作業の前に必ず `git pull`。** `data/` は毎日ボットがコミットするので、ローカルはすぐ遅れる。
  `data/*.json` を手元で編集してコミットしない（ボットの更新と衝突する）。
- **秘密情報は `.env` と GitHub の Repository secrets だけ。** 公開リポジトリなので、
  キー・トークン・個人のメールアドレスをコード・ログ・コミットに入れない。
- ワークフローの変更は、稼働中の自動更新の挙動を変える。push する前に相談する。
- Gemini のモデル名を変えるときは、そのモデルが使えることを先に確かめる（`check_models.py`）。
- 要約のプロンプトは「復帰する同僚に指導医が紹介する」設定。臨床アクションを中心に書かせる方針を変えない。

## 既知の事情

- 検索は「麻酔科領域 かつ ガイドライン・メタ解析・レビュー等」で、関連度順に 1 回 1 件を取る。
  2026-10-02 に注目キーワード（GLP-1 など）の縛りを外した。縛っていた頃は過去 1 年で 55 件しか当たらず、
  未処理がほぼ尽きて「新しい論文なし」の日が続いていた。
- 週次のワークフロー（`weekly_digest.yml`）は 2026-10-02 に削除した。毎日版と同じ処理を月曜にもう一度走らせるだけで、
  コミット手順の不具合により新しい論文の無い週は失敗していたため。
- 2026-02 時点のローカル作業のうち取り込んでいないもの（新しい順への並び替え、候補を多めに取る処理、取得件数 5、
  デバッグ用スクリプト）は、ローカルの `local-wip-2026-02` ブランチに残してある（未 push）。
