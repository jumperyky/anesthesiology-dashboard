import os
import requests
import logging
from dotenv import load_dotenv

# ロガーの設定
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_MESSAGING_API_BROADCAST = "https://api.line.me/v2/bot/message/broadcast"

def send_line_broadcast(text):
    """LINE Messaging API (Broadcast) でメッセージを送信する"""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN is not set. Skipping notification.")
        return

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Messaging API payload
    data = {
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    
    try:
        response = requests.post(LINE_MESSAGING_API_BROADCAST, headers=headers, json=data)
        response.raise_for_status()
        logger.info("LINE broadcast sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send LINE broadcast: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            logger.error(f"API Response: {response.text}")

def notify_new_papers(summarized_papers):
    """新規論文の通知メッセージを作成して送信する"""
    if not summarized_papers:
        logger.info("No new papers to notify.")
        return

    # Count papers
    count = len(summarized_papers)
    
    # Sort by importance descending
    summarized_papers.sort(key=lambda x: x.get('importance', 0), reverse=True)
    top_paper = summarized_papers[0]

    # メッセージ作成
    # Header
    message = f"【Anesth Update】今日のピックアップ\n\n"
    
    # Top Paper Info
    title = top_paper.get('title_ja', 'No Title')
    importance = top_paper.get('importance', '?')
    action = top_paper.get('clinical_action', 'N/A')
    
    # シンプルな表示に変更
    message += f"■ {title} (重要度: {importance})\n\n"
    # Clinical Actionは長くなるためLINEではSummaryを表示し、詳細はダッシュボードへ誘導
    summary = top_paper.get('summary', 'N/A')
    message += f"要約:\n{summary}\n\n"
    
    # Footer
    # 注: Messaging APIは1つの吹き出しで最大2000文字等の制限があるが、
    # この程度の分量ならまず問題ない。
    message += "詳細はダッシュボードを確認:\n"
    # ※デプロイ後は実際のURL (例: https://appname.streamlit.app) に書き換えてください
    message += "https://anesthesiology-dashboard-3fnm8vtwydla8zstrmsx8q.streamlit.app/" 
    
    send_line_broadcast(message)
