import logging
import sys
from datetime import datetime
from src.fetcher import fetch_papers, mark_as_processed
from src.summarizer import summarize_paper
from src.notifier import notify_new_papers
from src.utils import load_json, save_json

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

PAPERS_JSON_PATH = "data/papers.json"

def main():
    logger.info("Starting batch process...")
    
    # 1. Fetch Papers
    try:
        raw_papers = fetch_papers(max_results=1)
    except Exception as e:
        logger.error(f"Failed to fetch papers: {e}")
        return

    if not raw_papers:
        logger.info("No new papers found.")
        return

    logger.info(f"Fetched {len(raw_papers)} new papers. Starting summarization...")

    # 2. Summarize Papers
    summarized_papers = []
    processed_ids = []

    for paper in raw_papers:
        try:
            summary_data = summarize_paper(paper)
            # 取得日を追加
            summary_data['fetched_date'] = datetime.now().isoformat()
            summarized_papers.append(summary_data)
            processed_ids.append(paper['id'])
        except Exception as e:
            logger.error(f"Error summarising paper {paper.get('id', 'unknown')}: {e}")
            continue

    if not summarized_papers:
        logger.warning("No papers were successfully summarized.")
        return

    # 3. Save Data (Append to existing)
    try:
        existing_papers = load_json(PAPERS_JSON_PATH, [])
        # 新しいものが先頭に来るようにマージする場合:
        # updated_papers = summarized_papers + existing_papers
        # あるいは単純に追加して表示側でソート。今回はリストの末尾に追加する。
        updated_papers = existing_papers + summarized_papers
        save_json(PAPERS_JSON_PATH, updated_papers)
        logger.info(f"Saved {len(summarized_papers)} new papers to {PAPERS_JSON_PATH}")
    except Exception as e:
        logger.error(f"Failed to save papers.json: {e}")
        # 保存に失敗したら通知もしない方が安全かもしれないが、
        # IDの記録だけ失敗して再通知されるのを防ぐため、ここではエラーでもID記録に進むか検討。
        # 今回は安全倒しでリターンする（重複通知覚悟）
        return

    # 4. Mark IDs as processed
    try:
        mark_as_processed(processed_ids)
        logger.info(f"Marked {len(processed_ids)} IDs as processed.")
    except Exception as e:
        logger.error(f"Failed to update processed_ids.json: {e}")

    # 5. Notify
    try:
        notify_new_papers(summarized_papers)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

    logger.info("Batch process completed successfully.")

if __name__ == "__main__":
    main()
