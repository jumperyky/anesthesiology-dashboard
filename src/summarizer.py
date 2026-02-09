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

def summarize_paper(paper):
    """
    論文のAbstractをもとにGeminiで要約を生成する。
    (google-genai SDK v1.0+ 使用)
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # モデル設定
    # ユーザー環境で利用可能な最新モデルを指定
    model_name = "gemini-2.5-flash" 

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

    try:
        logger.info(f"Summarizing paper: {paper['id']} with {model_name}")
        
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
        
        # Add original paper info
        result['original_title'] = paper['title']
        result['url'] = paper['url']
        result['id'] = paper['id']
        result['pub_date'] = paper['pub_date']
        result['abstract'] = paper.get('abstract', '')
        
        # APIのRate Limit考慮
        time.sleep(1) 
        
        return result

    except Exception as e:
        logger.error(f"Failed to summarize paper {paper['id']}: {e}")
        return {
            "title_ja": "要約エラー",
            "summary": "要約の生成に失敗しました。",
            "clinical_action": "原文を確認してください。",
            "importance": 1,
            "original_title": paper['title'],
            "url": paper['url'],
            "id": paper['id'],
            "pub_date": paper['pub_date'],
            "abstract": paper.get('abstract', '')
        }
