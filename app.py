import streamlit as st
import pandas as pd
from src.utils import load_json
from datetime import datetime
import streamlit.components.v1 as components

# ページ設定
st.set_page_config(
    page_title="Anesth Update",
    page_icon="💉",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSSによるスタイリング
st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .stAlert {
        padding: 0.5rem 1rem;
    }
    .paper-card {
        background-color: #f9f9f9;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        border: 1px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .recent-list-item {
        padding: 10px;
        border-bottom: 1px solid #eee;
        cursor: pointer;
    }
    .recent-list-item:hover {
        background-color: #f0f2f6;
    }
    h3 {
        color: #333;
    }
    .pub-date {
        color: #666;
        font-size: 0.9em;
    }
    </style>
    """, unsafe_allow_html=True)

def copy_to_clipboard(text):
    """
    Copy text to clipboard using JavaScript with fallback for non-HTTPS environments.
    """
    safe_text = text.replace('"', '&quot;').replace("'", "\\'")
    
    html_code = f"""
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <input type="text" value="{text}" id="copyInput" style="flex: 1; padding: 5px; border: 1px solid #ccc; border-radius: 4px; border-right: none; border-top-right-radius: 0; border-bottom-right-radius: 0;" readonly>
        <button onclick="copyToClipboard()" style="padding: 5px 10px; background-color: #007bff; color: white; border: 1px solid #007bff; border-radius: 4px; border-top-left-radius: 0; border-bottom-left-radius: 0; cursor: pointer;">Copy</button>
    </div>
    <div id="status" style="font-size: 0.8em; color: green; height: 20px;"></div>

    <script>
    function copyToClipboard() {{
        var copyText = document.getElementById("copyInput");
        copyText.select();
        copyText.setSelectionRange(0, 99999); 

        try {{
            if (navigator.clipboard) {{
                navigator.clipboard.writeText(copyText.value).then(function() {{
                    document.getElementById("status").innerText = "Copied!";
                    setTimeout(function() {{ document.getElementById("status").innerText = ""; }}, 2000);
                }}, function(err) {{
                    fallbackCopyTextToClipboard(copyText.value);
                }});
            }} else {{
                fallbackCopyTextToClipboard(copyText.value);
            }}
        }} catch (err) {{
            fallbackCopyTextToClipboard(copyText.value);
        }}
    }}

    function fallbackCopyTextToClipboard(text) {{
        var textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.top = "0";
        textArea.style.left = "0";
        textArea.style.position = "fixed";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {{
            var successful = document.execCommand('copy');
            if (successful) {{
                document.getElementById("status").innerText = "Copied!";
                setTimeout(function() {{ document.getElementById("status").innerText = ""; }}, 2000);
            }} else {{
                document.getElementById("status").innerText = "Failed";
            }}
        }} catch (err) {{
            document.getElementById("status").innerText = "Failed";
        }}
        document.body.removeChild(textArea);
    }}
    </script>
    """
    components.html(html_code, height=80)

# データの読み込み
PAPERS_FILE = "data/papers.json"
papers = load_json(PAPERS_FILE, [])

# サイドバー
st.sidebar.title("Configuration")
notebook_lm_url = "https://notebooklm.google.com/"
st.sidebar.link_button("🚀 Open NotebookLM", notebook_lm_url)
st.sidebar.markdown("---")
st.sidebar.info("毎日更新: 最新の論文1件をピックアップ")

if not papers:
    st.info("No papers available.")
else:
    # 1. データの整理とソート (新しい順 -> fetched_date優先, なければpub_date)
    # 日付フォーマットのばらつきを吸収してソートキーを作る
    def get_sort_key(p):
        fd = p.get('fetched_date')
        if fd: return fd
        pd_val = p.get('pub_date')
        if pd_val and pd_val != 'Unknown': return pd_val
        return '0000-00-00'

    sorted_papers = sorted(papers, key=get_sort_key, reverse=True)

    # 2. グルーピング
    # - Latest (Top 1)
    # - Recent (Past 7 days excluding Top 1)
    # - Archive (Older)
    
    # ここではシンプルに「件数」で区切るか、「日付」で区切るか。
    # 要望: "毎朝1個ずつの更新...過去1週間分はすぐにtapできるように"
    # -> index 0 が Today's Pick
    # -> index 1-7 が Past Week (approx)
    # -> index 8- が Archive
    
    latest_paper = sorted_papers[0]
    recent_papers = sorted_papers[1:8]  # Next 7 papers
    archive_papers = sorted_papers[8:]   # The rest

    # session_stateで表示する論文を管理
    if 'selected_paper_id' not in st.session_state:
        st.session_state.selected_paper_id = latest_paper.get('id')

    # リストから選択された場合の処理用コールバック
    def set_selected_paper(paper_id):
        st.session_state.selected_paper_id = paper_id
        # トップへスクロール（Streamlitの仕様上難しいが、再描画で上に戻ることを期待）

    # --- Main Display Area ---
    
    # 選択された論文を探す
    current_paper = next((p for p in sorted_papers if p.get('id') == st.session_state.selected_paper_id), latest_paper)

    # ヘッダー (LatestかPastか区別しやすく)
    if current_paper == latest_paper:
        st.caption("🌟 Today's Pick")
    elif current_paper in recent_papers:
        st.caption("📅 Recent Update")
    else:
        st.caption("🗄 Archive")

    # タイトル
    st.title(current_paper.get('title_ja', 'No Title'))
    
    # メタ情報
    importance = current_paper.get('importance', 1)
    stars = "★" * importance
    pub_date = current_paper.get('pub_date', 'Unknown')
    st.markdown(f"**Importance:** <span style='color:orange'>{stars}</span> | **Published:** {pub_date}", unsafe_allow_html=True)
    
    st.markdown("---")

    # Clinical Action (最重要)
    st.info(f"#### 💡 Clinical Action\n\n{current_paper.get('clinical_action', 'N/A')}")
    
    # Summary
    st.markdown(f"#### 📝 Summary\n{current_paper.get('summary', 'N/A')}")
    
    st.markdown("---")
    
    # 詳細情報 (Expandable)
    with st.expander("Details & Source", expanded=False):
        st.markdown("**PubMed URL**:")
        copy_to_clipboard(current_paper.get('url', ''))
        st.markdown("---")
        st.markdown(f"**Original Title:** {current_paper.get('original_title', '')}")
        st.markdown(f"**Abstract:**\n{current_paper.get('abstract', 'No abstract available')}")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Navigation Area (Bottom) ---
    st.header("📚 Past Updates")
    
    # タブで「最近（1週間）」と「アーカイブ」を分ける
    tab1, tab2 = st.tabs(["Recent (Past 7)", "Archives"])
    
    with tab1:
        if not recent_papers:
            st.write("No recent papers.")
        else:
            for p in recent_papers:
                # ボタンとして配置し、クリックで選択状態を変更
                # ボタンのラベルに日付とタイトルを入れる
                date_str = p.get('fetched_date', '').split('T')[0] or p.get('pub_date', '')
                label = f"【{date_str}】 {p.get('title_ja', p.get('title', 'No Title'))[:40]}..."
                
                # keyにIDを使ってユニークにする
                if st.button(label, key=f"btn_{p.get('id')}", use_container_width=True):
                    set_selected_paper(p.get('id'))
                    st.rerun()

    with tab2:
        if not archive_papers:
            st.write("No archives.")
        else:
            # 1. Group by Year-Month
            archives_by_month = {}
            for p in archive_papers:
                # Use fetched_date or pub_date
                date_str = p.get('fetched_date')
                if not date_str:
                    date_str = p.get('pub_date', 'Unknown')
                
                # Extract YYYY-MM
                try:
                    # Try parsing ISO format first
                    dt = datetime.fromisoformat(date_str)
                    month_key = dt.strftime("%Y-%m")
                except ValueError:
                    # Fallback for simple date strings or unknown
                    month_key = date_str[:7] if len(date_str) >= 7 else "Others"
                
                if month_key not in archives_by_month:
                    archives_by_month[month_key] = []
                archives_by_month[month_key].append(p)

            # 2. Select Month
            # Sort months descending
            sorted_months = sorted(archives_by_month.keys(), reverse=True)
            
            selected_month = st.selectbox(
                "Select Month",
                options=sorted_months,
                key="archive_month_select"
            )

            # 3. Select Paper from that Month
            if selected_month:
                papers_in_month = archives_by_month[selected_month]
                
                archive_options = {f"{p.get('fetched_date', '').split('T')[0] or 'Unknown'} - {p.get('title_ja', '')[:30]}...": p.get('id') for p in papers_in_month}
                
                selected_archive_label = st.selectbox(
                    "Select Paper", 
                    options=list(archive_options.keys()),
                    key="archive_paper_select",
                    index=None,
                    placeholder="Choose a paper..."
                )
                
                if selected_archive_label:
                    selected_id = archive_options[selected_archive_label]
                    if st.button("View Selected Archive", key="view_archive_btn"):
                        set_selected_paper(selected_id)
                        st.rerun()

