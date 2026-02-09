import json
import os
import logging

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_json(filepath: str, default=None):
    """JSONファイルを読み込む。ファイルがない場合はdefaultを返す。"""
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}. Returning default value.")
        return default if default is not None else []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from {filepath}: {e}")
        return default if default is not None else []
    except Exception as e:
        logger.error(f"Error loading JSON from {filepath}: {e}")
        return default if default is not None else []

def save_json(filepath: str, data: any):
    """データをJSONファイルに保存する。"""
    try:
        # ディレクトリがない場合は作成
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved data to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}")
