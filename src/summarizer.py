import os
import json
import logging
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ロガーの設定
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# モデル設定。先頭から使い、混雑などで失敗し続けたら次のモデルへ切り替える
MODELS = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
# 1 モデルあたりの試行回数と、再試行までの待ち秒数（503 の高負荷は数十秒で戻ることが多い）
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = [10, 30]

class SummarizeError(Exception):
    """全モデル・全試行で要約できなかったとき。呼び出し側はこの論文を保存・通知しないこと。"""

def _is_retryable(e):
    """待てば回復しうるエラーか。日あたりの上限 (PerDay) は待っても戻らないので含めない。"""
    msg = str(e)
    if "PerDay" in msg:
        return False
    return any(s in msg for s in ("503", "UNAVAILABLE", "high demand", "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL", "504", "DEADLINE_EXCEEDED"))

def summarize_paper(paper):
    """
    論文のAbstractをもとにGeminiで要約を生成する。
    (google-genai SDK v1.0+ 使用)
    失敗し続けた場合は SummarizeError を投げる。エラー内容を要約の代わりに返さない
    (返すと「要約エラー」がそのまま保存・通知され、処理済み扱いで二度と要約し直されない)。
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    system_instruction = """
あなたは麻酔科の指導医です。1年間の育児休暇から復帰する同僚の麻酔科医に向けて、最新の論文を紹介してください。
目的は、基礎研究の結果を伝えることではなく、「明日の臨床でどう動くべきか」「この1年で変化した常識やピットフォール」を具体的かつ実践的に伝えることです。

提供された論文のタイトルとAbstractを読み、以下のJSON形式で出力してください。

{
  "title_ja": "論文の日本語タイトル",
  "summary": "3行程度の簡潔な要約（「〜である」調）",
  "clinical_action": "臨床現場での具体的なアクション指針や注意点（挨拶や前置きは不要。推奨事項や注意点から書き始めてください）",
  "importance": 5 (1〜5の整数。5が最重要)
}
日本語で出力してください。
"""

    prompt = f"""
Title: {paper['title']}
Abstract: {paper['abstract']}
"""

    last_error = None
    for model_name in MODELS:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                logger.info(f"Summarizing paper: {paper['id']} with {model_name} (attempt {attempt}/{MAX_ATTEMPTS})")

                # https://github.com/googleapis/python-genai
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )

                # Parse JSON
                # response.text should contain the JSON string
                result = json.loads(response.text)
                if not isinstance(result, dict) or not result.get('title_ja') or not result.get('summary'):
                    raise ValueError(f"unexpected response shape: {str(response.text)[:200]}")

                # Add original paper info
                result['original_title'] = paper['title']
                result['url'] = paper['url']
                result['id'] = paper['id']
                result['pub_date'] = paper['pub_date']
                result['abstract'] = paper.get('abstract', '')
                result['model'] = model_name

                # APIのRate Limit考慮
                time.sleep(1)

                return result

            except Exception as e:
                last_error = e
                # 形の崩れた応答は同じモデルでもう一度試す価値がある
                retryable = _is_retryable(e) or isinstance(e, (json.JSONDecodeError, ValueError))
                logger.warning(f"Failed to summarize paper {paper['id']} with {model_name} (attempt {attempt}/{MAX_ATTEMPTS}): {e}")
                if not retryable:
                    break  # 待っても回復しないので次のモデルへ
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_WAIT_SECONDS[attempt - 1])

    logger.error(f"Failed to summarize paper {paper['id']} with all models: {last_error}")
    raise SummarizeError(f"paper {paper['id']}: {last_error}")
