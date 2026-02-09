import os
from Bio import Entrez
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import logging
from .utils import load_json, save_json

# ロガーの取得
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()
Entrez.email = os.getenv("EMAIL")

PROCESSED_IDS_PATH = "data/processed_ids.json"

def fetch_papers(max_results=5):
    """
    PubMedから論文を取得し、重複を除外して返す。
    """
    if not Entrez.email:
        logger.error("EMAIL environment variable is not set.")
        raise ValueError("EMAIL environment variable is required for PubMed API.")

    # 1. 検索クエリの構築
    # Base topics
    base_query = '(Anesthesiology[Title/Abstract] OR "Perioperative care"[Title/Abstract])'
    
    # Important Keywords (OR condition)
    keywords = [
        '"GLP-1"', '"SGLT2"', '"Video Laryngoscope"', 
        '"Regional Anesthesia"', '"POCUS"', '"Frailty"'
    ]
    keywords_query = "(" + " OR ".join(keywords) + ")"
    
    # Publication Types / Focus (AND condition)
    types_query = '(Guideline[Publication Type] OR "Consensus Development Conference"[Publication Type] OR "Meta-Analysis"[Publication Type] OR "Systematic Review"[Publication Type] OR "Review"[Publication Type])'
    
    # Exclusions (NOT condition)
    exclusions = '(NOT "Animals"[MeSH Terms] NOT "Case Reports"[Publication Type])'
    
    # Full Query
    # (Base AND Keywords AND Types) NOT Exclusions
    # Note: ユーザー要望により Guideline 等を重視するが、Keywordが含まれているものを優先したい意図があるため
    # Base と Keywords は AND で結ぶことで、麻酔科領域かつ注目キーワードを含むものに絞る。
    # さらに Guideline/Meta-analysis 等で絞り込む。
    
    final_query = f"{base_query} AND {keywords_query} AND {types_query} {exclusions}"
    
    logger.info(f"Searching PubMed with query: {final_query}")

    try:
        # 2. ID検索 (reldate=365 で過去1年)
        handle = Entrez.esearch(
            db="pubmed",
            term=final_query,
            retmax=100,  # 重複排除用にある程度多く取得
            reldate=365,
            datetype="pdat",
            sort="relevance" # 関連度順
        )
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record["IdList"]
        logger.info(f"Found {len(id_list)} papers.")
        
        # 3. 重複排除
        processed_ids = load_json(PROCESSED_IDS_PATH, [])
        new_ids = [pid for pid in id_list if pid not in processed_ids]
        
        logger.info(f"New papers after duplicate check: {len(new_ids)}")
        
        if not new_ids:
            return []
        
        # 指定件数だけ処理
        target_ids = new_ids[:max_results]
        
    # 4. 詳細取得
        handle = Entrez.efetch(
            db="pubmed",
            id=target_ids,
            rettype="medline",
            retmode="xml"
        )
        papers_xml = Entrez.read(handle)
        handle.close()
        
        # タイトル重複チェック用
        existing_papers = load_json("data/papers.json", [])
        
        def normalize_title(t):
            if not t: return ""
            import re
            s = t.lower()
            s = re.sub(r'[^a-z0-9]', '', s)
            return s

        existing_titles = set()
        for p in existing_papers:
            # papers.json has 'original_title'
            ot = p.get('original_title')
            if ot:
                existing_titles.add(normalize_title(ot))
        
        papers_data = []
        if 'PubmedArticle' not in papers_xml:
             logger.warning("No PubmedArticle found in response.")
             return []

        skipped_count = 0
        for article in papers_xml['PubmedArticle']:
            medline_citation = article['MedlineCitation']
            article_data = medline_citation['Article']
            
            pmid = str(medline_citation['PMID'])
            title = article_data.get('ArticleTitle', 'No Title')
            
            # タイトル重複チェック
            # fetcherで取得したばかりのものは 'title' が英語タイトル
            if normalize_title(title) in existing_titles:
                logger.info(f"Skipping duplicate title (PMID: {pmid}): {title[:30]}...")
                skipped_count += 1
                continue

            # Abstractの取得 (リストの場合があるので結合)
            abstract_text = ""
            if 'Abstract' in article_data and 'AbstractText' in article_data['Abstract']:
                abstract_parts = article_data['Abstract']['AbstractText']
                if isinstance(abstract_parts, list):
                    abstract_text = " ".join([str(part) for part in abstract_parts])
                else:
                    abstract_text = str(abstract_parts)
            
            # 出版日の取得 (Journal Issue PubDate優先)
            pub_date_str = ""
            try:
                journal_issue = article_data['Journal']['JournalIssue']
                pub_date = journal_issue['PubDate']
                year = pub_date.get('Year', '')
                month = pub_date.get('Month', '')
                day = pub_date.get('Day', '')
                pub_date_str = f"{year}-{month}-{day}".strip("-")
            except:
                pub_date_str = "Unknown"

            papers_data.append({
                "id": pmid,
                "title": title,
                "abstract": abstract_text,
                "pub_date": pub_date_str,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
        
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} papers due to title duplication.")
            
        return papers_data

    except Exception as e:
        logger.error(f"Error occurred during fetching papers: {e}")
        return []

def mark_as_processed(paper_ids):
    """処理済みIDを保存する"""
    processed_ids = load_json(PROCESSED_IDS_PATH, [])
    # 重複を避けて追加
    updated_ids = list(set(processed_ids + paper_ids))
    save_json(PROCESSED_IDS_PATH, updated_ids)

if __name__ == "__main__":
    # for testing
    logging.basicConfig(level=logging.INFO)
    papers = fetch_papers()
    print(f"Fetched {len(papers)} papers.")
    for p in papers:
        print(f"- {p['title']}")
