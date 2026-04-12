import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="在庫検索アプリ", layout="wide")
st.title("📦 パレット在庫検索システム")

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

try:
    client = get_client()
    if client:
        SPREADSHEET_ID = '1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk'
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet("フォームの回答 1")
        
        all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')

        if len(all_values) >= 4:
            p_idx = 26 
            raw_data = all_values[3:] 
            data_list = []
           
            for row in raw_data:
                if len(row) > p_idx:
                    p_val = str(row[p_idx]).strip()
                    if p_val and p_val not in ["", "#N/A", "None", "nan"]:
                        data_list.append([
                            p_val,                                    
                            serial_to_datetime(row[p_idx+1]) if len(row) > p_idx+1 else "", 
                            str(row[p_idx+3]) if len(row) > p_idx+3 else "",               
                            str(row[p_idx+5]) if len(row) > p_idx+5 else "",               
                            str(row[p_idx+7]) if len(row) > p_idx+7 else "",               
                            str(row[p_idx+9]) if len(row) > p_idx+9 else "",               
                            str(row[p_idx+11]) if len(row) > p_idx+11 else ""              
                        ])
           
            df = pd.DataFrame(data_list, columns=["パレット番号", "日時", "商品名", "元エリア", "移動エリア", "コード", "担当者"])

            # --- 検索機能の強化 ---
            st.write("### 🔍 在庫を探す")
            col1, col2 = st.columns(2)
            with col1:
                target_no = st.text_input("① パレット番号で検索 (例: 135)")
            with col2:
                target_name = st.text_input("② 商品名で曖昧検索 (例: 屋根)")

            # 1. 番号で検索された場合
            if target_no:
                search_val = str(target_no).strip()
                def normalize_num(s):
                    s = str(s).strip()
                    if s.endswith('.0'): s = s[:-2]
                    return s

                match_row = df[df["パレット番号"].apply(normalize_num) == normalize_num(search_val)]
               
                if match_row.empty:
                    st.error(f"番号「{search_val}」は見つかりませんでした。")
                else:
                    latest = match_row.iloc[-1]
                    product_name = latest["商品名"]
                    st.success(f"✅ パレット {search_val} は現在 「{product_name}」 です")
                    
                    # 同じ商品の在庫一覧（工場内除外）
                    all_stock = df[df["商品名"] == product_name]
                    available_stock = all_stock[~all_stock["移動エリア"].str.contains("工場内", na=False)]
                    st.write(f"📍 「{product_name}」の有効な在庫一覧")
                    st.dataframe(available_stock, use_container_width=True, hide_index=True)

            # 2. 商品名で曖昧検索された場合
            elif target_name:
                # 工場内を除外したデータから、文字が含まれるものを抽出
                filtered_df = df[~df["移動エリア"].str.contains("工場内", na=False)]
                results = filtered_df[filtered_df["商品名"].str.contains(target_name, na=False)]
                
                if results.empty:
                    st.warning(f"「{target_name}」を含む在庫は見つかりませんでした。")
                else:
                    st.success(f"✅ 「{target_name}」を含む在庫が {len(results)} 件見つかりました")
                    st.dataframe(results, use_container_width=True, hide_index=True)
            
            else:
                st.info("番号または商品名を入力してください。")

        else:
            st.info("データが足りません。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")

st.markdown("---")
st.link_button("👉 フォームを開く", "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing")
