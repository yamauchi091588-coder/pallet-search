import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import unicodedata
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- サイドバーでメニュー切り替え ---
st.sidebar.title("メニュー選択")
mode = st.sidebar.radio("検索モードを選択してください", ["形材検索（パレット）", "部品検索"])

# --- 共通のGoogleシート接続設定 ---
@st.cache_resource
def get_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        return gspread.authorize(Credentials.from_service_account_file('spread-sheet-01.json', scopes=scope))
    except Exception as e:
        st.error(f"鍵ファイルの読み込み失敗: {e}")
        return None

# 全角・半角を統一して検索しやすくする関数
def normalize_text(text):
    if not text:
        return ""
    # 全角を半角に、大文字を小文字に変換して比較しやすくする
    return unicodedata.normalize('NFKC', str(text)).lower().strip()

def serial_to_datetime(serial):
    try:
        serial = float(serial)
        base_date = datetime(1899, 12, 30)
        return (base_date + timedelta(days=serial)).strftime('%m/%d %H:%M')
    except:
        return str(serial)

# --- 1. 形材検索モード ---
if mode == "形材検索（パレット）":
    st.title("📦 形材（パレット）在庫検索")
    
    try:
        client = get_client()
        if client:
            SPREADSHEET_ID = '1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk'
            sh = client.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet("フォームの回答 1")
            all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')

            if len(all_values) >= 4:
                p_idx = 26 # AA列
                raw_data = all_values[3:] 
                data_list = []
               
                for row in raw_data:
                    if len(row) > p_idx:
                        p_val = str(row[p_idx]).strip()
                        if p_val and p_val not in ["", "#N/A", "None", "nan"]:
                            honsu = str(row[p_idx+13]) if len(row) > p_idx+13 else "0"
                            data_list.append({
                                "パレット番号": p_val,
                                "日時": serial_to_datetime(row[p_idx+1]) if len(row) > p_idx+1 else "",
                                "商品名": str(row[p_idx+3]) if len(row) > p_idx+3 else "",
                                "本数": honsu,
                                "元エリア": str(row[p_idx+5]) if len(row) > p_idx+5 else "",
                                "移動エリア": str(row[p_idx+7]) if len(row) > p_idx+7 else "",
                                "コード": str(row[p_idx+9]) if len(row) > p_idx+9 else "",
                                "担当者": str(row[p_idx+11]) if len(row) > p_idx+11 else ""
                            })
                df = pd.DataFrame(data_list)
                
                st.write("### 🔍 在庫を探す")
                col1, col2 = st.columns(2)
                with col1:
                    target_no = st.text_input("① パレット番号で検索")
                with col2:
                    target_name = st.text_input("② 商品名で曖昧検索（全角OK）")

                df_display = df[~df["移動エリア"].str.contains("工場内", na=False)]

                if target_no:
                    search_val = normalize_text(target_no)
                    # 番号も正規化して検索
                    df["temp_no"] = df["パレット番号"].apply(normalize_text)
                    match_row = df[df["temp_no"] == search_val]
                    if match_row.empty:
                        st.error(f"番号「{target_no}」は見つかりませんでした。")
                    else:
                        latest = match_row.iloc[-1]
                        product_name = latest["商品名"]
                        st.success(f"✅ パレット {target_no} は現在 「{product_name}」 ({latest['本数']}本) です")
                        results = df_display[df_display["商品名"] == product_name]
                        st.dataframe(results, use_container_width=True, hide_index=True)
                elif target_name:
                    search_name = normalize_text(target_name)
                    # 商品名を正規化した一時的な列で検索
                    df_display_temp = df_display.copy()
                    df_display_temp["temp_name"] = df_display_temp["商品名"].apply(normalize_text)
                    results = df_display_temp[df_display_temp["temp_name"].str.contains(search_name, na=False)]
                    
                    if results.empty:
                        st.warning(f"「{target_name}」を含む在庫は見つかりませんでした。")
                    else:
                        st.success(f"✅ 「{target_name}」を含む在庫が見つかりました")
                        st.dataframe(results.drop(columns=["temp_name"]), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.link_button("👉 形材移動の入力（フォーム）を開く", "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# --- 2. 部品検索モード ---
elif mode == "部品検索":
    st.title("⚙️ 部品在庫検索")
    
    try:
        client = get_client()
        if client:
            SPREADSHEET_ID = '1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk'
            sh = client.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet("部品マスター")
            all_values = worksheet.get_all_values()

            if len(all_values) > 1:
                data_list = []
                for row in all_values[1:]:
                    if len(row) >= 5:
                        data_list.append({
                            "場所": row[2],
                            "品目コード": row[3],
                            "部品名": row[4]
                        })
                
                df_parts = pd.DataFrame(data_list)
                
                query = st.text_input("部品名を入力してください（全角OK）", key="parts_search")
                
                if query:
                    search_query = normalize_text(query)
                    # 部品名を正規化した一時的な列で検索
                    df_parts["temp_name"] = df_parts["部品名"].apply(normalize_text)
                    results = df_parts[df_parts["temp_name"].str.contains(search_query, na=False)]
                    
                    if results.empty:
                        st.warning(f"「{query}」に一致する部品は見つかりませんでした。")
                    else:
                        st.success(f"✅ {len(results)} 件見つかりました")
                        
                        for index, row in results.iterrows():
                            with st.container():
                                col_info, col_bc = st.columns([2, 1])
                                with col_info:
                                    st.subheader(f"🔹 {row['部品名']}")
                                    st.write(f"📍 **場所**: {row['場所']}")
                                    st.write(f"🔢 **コード**: {row['品目コード']}")
                                
                                with col_bc:
                                    # バーコード背景を白にするためのCSSとHTML
                                    bc_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={row['品目コード']}&scale=2&rotate=N&includetext"
                                    # 白背景の枠の中にバーコードを表示
                                    st.markdown(
                                        f"""
                                        <div style="background-color: white; padding: 10px; border-radius: 5px; display: inline-block;">
                                            <img src="{bc_url}" style="max-width: 100%;">
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                st.divider()
            else:
                st.info("部品マスターにデータがありません。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
