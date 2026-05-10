import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
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
                    target_name = st.text_input("② 商品名で曖昧検索")

                df_display = df[~df["移動エリア"].str.contains("工場内", na=False)]

                if target_no:
                    search_val = str(target_no).strip()
                    match_row = df[df["パレット番号"].astype(str).str.contains(search_val, na=False)]
                    if match_row.empty:
                        st.error(f"番号「{search_val}」は見つかりませんでした。")
                    else:
                        latest = match_row.iloc[-1]
                        product_name = latest["商品名"]
                        st.success(f"✅ パレット {search_val} は現在 「{product_name}」 ({latest['本数']}本) です")
                        results = df_display[df_display["商品名"] == product_name]
                        st.dataframe(results, use_container_width=True, hide_index=True)
                elif target_name:
                    results = df_display[df_display["商品名"].str.contains(target_name, na=False)]
                    if results.empty:
                        st.warning(f"「{target_name}」を含む在庫は見つかりませんでした。")
                    else:
                        st.success(f"✅ 「{target_name}」を含む在庫が {len(results)} 件見つかりました")
                        st.dataframe(results, use_container_width=True, hide_index=True)

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
            # 6番目のシート「部品マスター」を取得
            worksheet = sh.worksheet("部品マスター")
            all_values = worksheet.get_all_values()

            if len(all_values) > 1:
                # C列(場所):2, D列(品目コード):3, E列(部品名):4
                data_list = []
                for row in all_values[1:]: # ヘッダー除外
                    if len(row) >= 5:
                        data_list.append({
                            "場所": row[2],
                            "品目コード": row[3],
                            "部品名": row[4]
                        })
                
                df_parts = pd.DataFrame(data_list)
                
                query = st.text_input("部品名を入力してください（曖昧検索）", key="parts_search")
                
                if query:
                    results = df_parts[df_parts["部品名"].str.contains(query, na=False)]
                    
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
                                    # バーコード画像の生成 (Google Charts API)
                                    # コード39形式、高さ60px、幅200px
                                    bc_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={row['品目コード']}&scale=2&rotate=N&includetext"
                                    st.image(bc_url, caption="バーコード")
                                st.divider()
            else:
                st.info("部品マスターにデータがありません。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
