import json
import logging
import os
import time
from dotenv import load_dotenv
from src.utils import load_json, save_json
from src.summarizer import summarize_paper

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

PAPERS_FILE = "data/papers.json"

def fix_data():
    logger.info("Starting data fix process...")
    papers = load_json(PAPERS_FILE, [])
    
    if not papers:
        logger.info("No papers found.")
        return

    # 1. Deduplication (Existing duplicates)
    # ユーザー指摘の重複を解消する。
    
    def normalize_title(t):
        if not t: return ""
        # 小文字化して、英数字以外を除去
        import re
        s = t.lower()
        s = re.sub(r'[^a-z0-9]', '', s)
        return s
    
    unique_papers = []
    seen_titles = set()
    duplicates_removed = 0
    
    # papers.json のデータ構造では英語タイトルは 'original_title' にある。
    # しかし、fetcherから来たばかりのデータ構造(fetcher内での処理)では 'title' にある。
    # ここは papers.json の修復なので 'original_title' を見る。
    # なければ 'title' (日本語タイトルに上書きされている可能性があるが...) あるいは 'title_ja' は日本語なのでここでは使えない。
    # original_title がない場合、title_ja からの重複判断は難しいので、original_title があるものだけで判断する。

    for paper in papers:
        # original_title が無ければそのペーパーは重複チェック対象外（残す）
        raw_title = paper.get('original_title')
        if not raw_title:
             # フォールバック: fetcher直後のデータならtitleにあるかも？
             raw_title = paper.get('title')
        
        if not raw_title:
            unique_papers.append(paper)
            continue
            
        norm_title = normalize_title(raw_title)
        
        if norm_title in seen_titles:
            logger.info(f"Removing duplicate: {paper.get('id')} - {raw_title[:30]}...")
            duplicates_removed += 1
            continue
        
        seen_titles.add(norm_title)
        unique_papers.append(paper)
        
    logger.info(f"Removed {duplicates_removed} duplicates.")
    
    # 2. Fix Errors
    # title_ja が "要約エラー" などのものを再実行
    updated_papers = []
    fixed_count = 0
    
    for paper in unique_papers:
        if paper.get('title_ja') == "要約エラー" or paper.get('summary') == "要約の生成に失敗しました。":
            logger.info(f"Re-summarizing paper: {paper.get('id')}")
            
            # summarize_paper は paper オブジェクト(fetcher形式)を期待するが、
            # papers.json の paper は既に加工されている。
            # summarizer.py は paper['title'] と paper['abstract'] を使う。
            # papers.json には title (Original) がない場合もある？ 
            # -> summarizer.py の出力で original_title に入れている。
            # -> fetcher形式に合わせる必要がある。
            
            # 再構築するためのデータ
            reconstruct_paper = {
                "id": paper.get('id'),
                "title": paper.get('original_title', paper.get('title')), # original_titleがあればそれを使う
                "abstract": paper.get('abstract', ''), # abstract は詳細欄のために保存していないと消えてるかも？
                # app.pyを見ると 'abstract' キーはあるみたいだが、要約エラー時は abstract を保存しているか？
                # summarizer.py のエラー処理ブロックでは abstract: paper.get('abstract') を保存している。OK。
                "url": paper.get('url'),
                "pub_date": paper.get('pub_date')
            }
            
            if not reconstruct_paper['abstract']:
                logger.warning(f"Paper {paper.get('id')} has no abstract. Skipping re-summarization.")
                updated_papers.append(paper)
                continue
                
            try:
                # new_result は辞書
                new_result = summarize_paper(reconstruct_paper)
                
                # fetched_date は元のを維持したいが、エラー時は入ってないかも？
                # 入っていれば維持
                if 'fetched_date' in paper:
                    new_result['fetched_date'] = paper['fetched_date']
                
                updated_papers.append(new_result)
                fixed_count += 1
                logger.info(f"Fixed paper: {paper.get('id')}")
            except Exception as e:
                logger.error(f"Failed to re-summarize {paper.get('id')}: {e}")
                updated_papers.append(paper) # 失敗したらそのまま
        else:
            updated_papers.append(paper)

    logger.info(f"Fixed {fixed_count} errors.")
    
    # Save
    save_json(PAPERS_FILE, updated_papers)
    logger.info("Data fix completed.")

if __name__ == "__main__":
    fix_data()
