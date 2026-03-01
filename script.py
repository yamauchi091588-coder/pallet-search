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
        # アップロードした鍵ファイル名と一致している必要があります
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
        # シート名が「フォームの回答 1」であることを確認してください
        worksheet = sh.worksheet("フォームの回答 1")
        
        # 全データを取得
        all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')

        # 画像に基づき、4行目（インデックス3）からデータ開始
        if len(all_values) >= 4:
            # AA列は27番目なのでインデックスは26
            p_idx = 26 
            raw_data = all_values[3:] 
            data_list = []
           
            for row in raw_data:
                if len(row) > p_idx:
                    p_val = str(row[p_idx]).strip()
                    if p_val and p_val not in ["", "#N/A", "None", "nan"]:
                        # 画像の列配置に合わせて取得（AA:番号, AB:日時, AC:商品名, AE:移動前, AF:移動後）
                        data_list.append([
                            p_val,                                    # AA: パレット番号
                            serial_to_datetime(row[p_idx+1]) if len(row) > p_idx+1 else "", # AB: 日時
                            str(row[p_idx+2]) if len(row) > p_idx+2 else "",               # AC: 商品名
                            str(row[p_idx+4]) if len(row) > p_idx+4 else "",               # AE: 移動前
                            str(row[p_idx+5]) if len(row) > p_idx+5 else "",               # AF: 移動後
                        ])
           
            df = pd.DataFrame(data_list, columns=["パレット番号", "日時", "商品名", "元エリア", "移動エリア"])

            target_no = st.text_input("検索したい番号を入力（例: 1）")

            if target_no:
                search_val = str(target_no).strip()
                # 数字の表記ゆれ（1.0 と 1 など）を吸収
                def normalize_num(s):
                    s = str(s).strip()
                    if s.endswith('.0'): s = s[:-2]
                    return s

                match_row = df[df["パレット番号"].apply(normalize_num) == normalize_num(search_val)]
               
                if match_row.empty:
                    st.error(f"番号「{search_val}」は見つかりませんでした。")
                else:
                    # 一番下の行（最新データ）を取得
                    latest = match_row.iloc[-1]
                    st.success(f"✅ 商品名：{latest['商品名']}")
                    
                    # 同じ商品の在庫をすべて表示
                    all_stock = df[df["商品名"] == latest["商品名"]]
                    st.write("### 📍 在庫エリア一覧")
                    st.dataframe(all_stock, use_container_width=True, hide_index=True)
        else:
            st.info("データが足りません（4行目以降にデータを入力してください）")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")

st.markdown("---")
st.link_button("👉 フォームを開く", "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing")
