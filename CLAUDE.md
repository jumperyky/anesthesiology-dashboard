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

- 検索式は `src/fetcher.py` の `build_query()`。2026-10-02 に作り直した。
  - 対象: 麻酔科のコア誌（`CORE_JOURNALS`）に載ったもの、または題名に麻酔そのものの語（`TOPIC_TITLE_TERMS`）があるもの
  - 種別: ガイドライン・コンセンサス・システマティックレビュー・メタ解析（`EVIDENCE_TYPES`）。ナラティブレビューは入れていない
  - 新しい順に並べ、1 回 1 件を取る。過去 1 年で約 540 件（1 日あたり約 1.5 件）
- 検索式を変えるときに知っておくこと:
  - `NOT` をかっこの先頭に置かない。以前の `(NOT "Animals"[MeSH Terms] NOT ...)` は先頭の `NOT` が PubMed に捨てられ、
    除外どころか「MeSH 付与済みであること」を要求する条件になっていた。esearch の `WarningList` で確かめられる
  - 題名の語に `perioperative` や `postoperative pain` を入れない。周術期化学療法や歯科の術後痛まで拾う
  - 総合誌の RCT を足すと、麻酔と関係のない周術期の腫瘍学の試験が混ざる
  - 以前の注目キーワード縛り（GLP-1 など）は過去 1 年で 55 件しか当たらず、未処理が尽きて「新しい論文なし」が続いた
- 候補は取得件数の 5 倍まで取り、タイトル重複を除いてから必要な件数に絞る。ちょうどの件数だけ取ると、
  それが重複で落ちたときに 0 件になり、処理済みにもならないので、毎回同じ論文で止まり続ける。
- 週次のワークフロー（`weekly_digest.yml`）は 2026-10-02 に削除した。毎日版と同じ処理を月曜にもう一度走らせるだけで、
  コミット手順の不具合により新しい論文の無い週は失敗していたため。
- 2026-02 時点のローカル作業のうち取り込んでいないもの（取得件数 5、Gemini を 2.0-flash に下げる変更、
  デバッグ用スクリプト）は、ローカルの `local-wip-2026-02` ブランチに残してある（未 push）。
