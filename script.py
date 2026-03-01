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
        # スプレッドシートID
        SPREADSHEET_ID = '1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk'
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet("フォームの回答 1")
        
        all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')

        # 4行目（インデックス3）からデータ開始
        if len(all_values) >= 4:
            # AA列 = インデックス26
            p_idx = 26 
            raw_data = all_values[3:] 
            data_list = []
           
            for row in raw_data:
                if len(row) > p_idx:
                    p_val = str(row[p_idx]).strip()
                    if p_val and p_val not in ["", "#N/A", "None", "nan"]:
                        # 教えていただいた列情報に基づき抽出
                        data_list.append([
                            p_val,                                    # AA: パレット番号
                            serial_to_datetime(row[p_idx+1]) if len(row) > p_idx+1 else "", # AB: 日時
                            str(row[p_idx+3]) if len(row) > p_idx+3 else "",               # AD: 商品名
                            str(row[p_idx+5]) if len(row) > p_idx+5 else "",               # AF: 移動前
                            str(row[p_idx+7]) if len(row) > p_idx+7 else "",               # AH: 移動後
                            str(row[p_idx+9]) if len(row) > p_idx+9 else "",               # AJ: 品目コード
                            str(row[p_idx+11]) if len(row) > p_idx+11 else ""              # AL: 担当者
                        ])
           
            df = pd.DataFrame(data_list, columns=["パレット番号", "日時", "商品名", "元エリア", "移動エリア", "コード", "担当者"])

            target_no = st.text_input("検索したい番号を入力（例: 1）")

            if target_no:
                search_val = str(target_no).strip()
                def normalize_num(s):
                    s = str(s).strip()
                    if s.endswith('.0'): s = s[:-2]
                    return s

                # 入力された番号と一致する行を探す
                match_row = df[df["パレット番号"].apply(normalize_num) == normalize_num(search_val)]
               
                if match_row.empty:
                    st.error(f"番号「{search_val}」は見つかりませんでした。半角数字で入力してください。")
                else:
                    # 最新の履歴（一番下の行）から商品名を特定
                    latest = match_row.iloc[-1]
                    product_name = latest["商品名"]
                    
                    st.success(f"✅ 商品名：{product_name}")
                    
                    # その商品が入っている全在庫を表示
                    st.write(f"### 📍 「{product_name}」の在庫一覧")
                    st.dataframe(
                        df[df["商品名"] == product_name],
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.info("データが4行目以降に見つかりませんでした。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")

st.markdown("---")
st.link_button("👉 フォームを開く", "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing")
