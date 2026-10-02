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

# 麻酔科のコア誌 (NLM の誌名略称)。ここに載った論文は、題名に「麻酔」が無くても麻酔科医向けとみなす
CORE_JOURNALS = [
    "Anesthesiology", "Br J Anaesth", "Anaesthesia", "Anesth Analg", "Reg Anesth Pain Med",
    "Eur J Anaesthesiol", "Can J Anaesth", "J Clin Anesth", "Acta Anaesthesiol Scand",
    "Anaesth Crit Care Pain Med", "J Cardiothorac Vasc Anesth", "Paediatr Anaesth",
    "Int J Obstet Anesth", "J Anesth", "Curr Opin Anaesthesiol", "BJA Educ",
    "Korean J Anesthesiol", "Minerva Anestesiol", "J Neurosurg Anesthesiol",
    "Perioper Med (Lond)",
]

# コア誌以外から拾うときの条件。題名に麻酔そのものの語があること。
# "perioperative" や "postoperative pain" は入れない (周術期化学療法や歯科の術後痛まで拾ってしまう)
TOPIC_TITLE_TERMS = [
    "anesthesia[ti]", "anaesthesia[ti]", "anesthetic*[ti]", "anaesthetic*[ti]",
    "anesthesiolog*[ti]", "anaesthesiolog*[ti]",
    '"nerve block"[ti]', '"nerve blocks"[ti]', '"plane block"[ti]', "neuraxial[ti]",
    '"airway management"[ti]', '"tracheal intubation"[ti]', "videolaryngoscop*[ti]",
    '"neuromuscular block"[ti]', '"neuromuscular blockade"[ti]',
    '"postoperative nausea"[ti]', '"malignant hyperthermia"[ti]',
]

# ガイドライン・コンセンサス・システマティックレビュー・メタ解析だけを拾う (ナラティブレビューは入れない)
EVIDENCE_TYPES = [
    "Guideline[pt]", '"Practice Guideline"[pt]', '"Consensus Statement"[pt]',
    '"Meta-Analysis"[pt]', '"Network Meta-Analysis"[pt]', '"Systematic Review"[pt]',
]

def build_query():
    """PubMed の検索式を組み立てる。"""
    journals = "(" + " OR ".join(f'"{j}"[ta]' for j in CORE_JOURNALS) + ")"
    topic = "(" + " OR ".join(TOPIC_TITLE_TERMS) + ")"
    types = "(" + " OR ".join(EVIDENCE_TYPES) + ")"

    # 除外条件。NOT はかっこの先頭に置かない。
    # 以前の "(NOT Animals[MeSH] NOT ...)" は先頭の NOT が PubMed に捨てられ、除外として効いていなかった
    exclusions = (
        " NOT (animals[mh] NOT humans[mh])"
        ' NOT ("Case Reports"[pt] OR Letter[pt] OR Comment[pt] OR Editorial[pt]'
        ' OR "Published Erratum"[pt] OR "Retracted Publication"[pt])'
        " NOT (protocol[ti] OR dental[ti] OR dentistry[ti] OR endodontic*[ti] OR veterinary[ti])"
    )
    # 抄録が無いと要約できない
    return f"(({journals} OR {topic}) AND {types}){exclusions} AND hasabstract AND English[lang]"

def fetch_papers(max_results=5):
    """
    PubMedから論文を取得し、重複を除外して返す。
    """
    if not Entrez.email:
        logger.error("EMAIL environment variable is not set.")
        raise ValueError("EMAIL environment variable is required for PubMed API.")

    # 1. 検索クエリの構築
    final_query = build_query()

    logger.info(f"Searching PubMed with query: {final_query}")

    try:
        # 2. ID検索 (reldate=365 で過去1年)
        handle = Entrez.esearch(
            db="pubmed",
            term=final_query,
            retmax=100,  # 重複排除用にある程度多く取得
            reldate=365,
            datetype="pdat",
            sort="pub_date" # 新しい順
        )
        record = Entrez.read(handle)
        handle.close()

        id_list = record["IdList"]
        logger.info(f"Found {len(id_list)} papers (newest first).")

        # 3. 重複排除
        processed_ids = load_json(PROCESSED_IDS_PATH, [])
        new_ids = [pid for pid in id_list if pid not in processed_ids]

        logger.info(f"New papers after duplicate check: {len(new_ids)}")

        if not new_ids:
            return []

        # 候補は多めに取り、下のタイトル重複チェックを通ったものを max_results 件まで集める。
        # ちょうど max_results 件だけ取ると、それが重複で落ちたときに 0 件になり、
        # 処理済みにもならないので、毎回同じ論文で止まり続ける
        candidate_ids = new_ids[:max_results * 5]

    # 4. 詳細取得
        handle = Entrez.efetch(
            db="pubmed",
            id=candidate_ids,
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
            if len(papers_data) >= max_results:
                break

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
