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
        st.error(f"鍵ファイルの読み込みに失敗しました: {e}")
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
        
        # すべてのデータを取得（列を自動判別するため）
        all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')

        if len(all_values) >= 1:
            # 1行目（ヘッダー）から「パレット番号」などの列を探す
            header = all_values[0]
            
            # 列番号を自動で見つける（もし「パレット番号」という名前の列があればそれを使う）
            # 見つからない場合は、これまでの設定通り27列目（インデックス26）を使います
            p_idx = 26
            for i, h in enumerate(header):
                if "パレット番号" in str(h):
                    p_idx = i
                    break

            raw_data = all_values[1:] # 2行目以降がデータ
            data_list = []
           
            for row in raw_data:
                if len(row) > p_idx:
                    p_val = str(row[p_idx]).strip()
                    # 空白やエラー値を除外
                    if p_val and p_val not in ["", "#N/A", "None", "nan"]:
                        # データの抽出（列の順番がズレていてもエラーにならないよう調整）
                        data_list.append([
                            p_val,                                    # パレット番号
                            serial_to_datetime(row[p_idx+1]) if len(row) > p_idx+1 else "", # 日時
                            str(row[p_idx+3]) if len(row) > p_idx+3 else "",               # 商品名
                            str(row[p_idx+5]) if len(row) > p_idx+5 else "",               # 元エリア
                            str(row[p_idx+7]) if len(row) > p_idx+7 else "",               # 移動エリア
                            str(row[p_idx+9]) if len(row) > p_idx+9 else "",               # コード
                            str(row[p_idx+11]) if len(row) > p_idx+11 else ""              # 担当者
                        ])
           
            df = pd.DataFrame(data_list, columns=["パレット番号", "日時", "商品名", "元エリア", "移動エリア", "コード", "担当者"])

            target_no = st.text_input("検索したい番号を入力（例: 135）")

            if target_no:
                search_val = str(target_no).strip()
                # 数字の比較を確実にする（135.0 と 135 を同じとみなす）
                def normalize_num(s):
                    s = str(s).strip()
                    if s.endswith('.0'): s = s[:-2]
                    return s

                match_row = df[df["パレット番号"].apply(normalize_num) == normalize_num(search_val)]
               
                if match_row.empty:
                    st.error(f"番号「{search_val}」は見つかりませんでした。現在登録されているパレット番号を確認してください。")
                else:
                    # 最新のデータを表示
                    latest_row = match_row.iloc[-1] 
                    product_name = latest_row["商品名"]
                    st.success(f"✅ 商品名：{product_name}")

                    # その商品が入っている場所を表示
                    results = df[df["商品名"] == product_name]

                    if not results.empty:
                        st.write("### 📍 在庫エリア一覧")
                        st.dataframe(results, use_container_width=True, hide_index=True)
        else:
            st.info("データが空です。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")

st.markdown("---")
st.write("### 📝 データの入力・更新")
form_url = "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing"
st.link_button("👉 フォームを開く", form_url)
