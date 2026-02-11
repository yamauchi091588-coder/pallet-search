import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import json

# アプリの基本設定
st.set_page_config(page_title="在庫検索アプリ", layout="wide")
st.title("📦 パレット在庫検索システム")

@st.cache_resource
def get_client():
    # 権限の範囲を設定
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # 【重要】GitHubのファイルではなく、StreamlitのSecretsから設定を読み込む
    try:
        # Secretsに保存した「gcp_service_account」という名前のデータを読み込む
        service_account_info = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Secretsの読み込みに失敗しました。設定を確認してください: {e}")
        return None

def serial_to_datetime(serial):
    try:
        serial = float(serial)
        base_date = datetime(1899, 12, 30)
        return (base_date + timedelta(days=serial)).strftime('%m/%d %H:%M')
    except:
        return str(serial)

# メイン処理
try:
    client = get_client()
    if client:
        # スプレッドシートのID
        SPREADSHEET_ID = '1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk'
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet("フォームの回答 1")
        
        # データを取得（計算結果もそのまま取得）
        all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')

        if len(all_values) >= 5:
            # 5行目以降がデータ
            raw_data = all_values[4:]
            data_list = []
           
            for row in raw_data:
                # パレット番号（27列目=インデックス26）があるか確認
                if len(row) > 37:
                    p_val = str(row[26]).strip()
                    if p_val and p_val not in ["", "#N/A", "None"]:
                        data_list.append([
                            p_val,                        # パレット番号
                            serial_to_datetime(row[27]),  # 日時
                            str(row[29]),                 # 商品名
                            str(row[31]),                 # 元エリア
                            str(row[33]),                 # 移動エリア
                            str(row[35]),                 # コード
                            str(row[37])                  # 担当者
                        ])
           
            df = pd.DataFrame(data_list, columns=["パレット番号", "日時", "商品名", "元エリア", "移動エリア", "コード", "担当者"])

            # 検索窓
            target_no = st.text_input("検索したい番号を入力（例: 135）")

            if target_no:
                search_val = str(target_no).strip()
                # 数値の表記ゆれ対策（135 と 135.0 を同じに扱う）
                def normalize_num(s):
                    s = str(s).strip()
                    if s.endswith('.0'): s = s[:-2]
                    return s

                match_row = df[df["パレット番号"].apply(normalize_num) == normalize_num(search_val)]
               
                if match_row.empty:
                    st.error(f"番号「{search_val}」は見つかりませんでした。")
                else:
                    product_name = match_row.iloc[0]["商品名"]
                    st.success(f"✅ 商品名：{product_name}")

                    # 同じ商品名かつ「工場内」を含まない在庫を抽出
                    results = df[
                        (df["商品名"] == product_name) &
                        (~df["元エリア"].str.contains("工場内", na=False)) &
                        (~df["移動エリア"].str.contains("工場内", na=False))
                    ]

                    if not results.empty:
                        st.write("### 📍 在庫エリア一覧")
                        st.dataframe(
                            results,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "パレット番号": st.column_config.TextColumn("No.", width="small"),
                                "日時": st.column_config.TextColumn("日時", width="small"),
                                "商品名": st.column_config.TextColumn("商品名", width="medium"),
                                "元エリア": st.column_config.TextColumn("元", width="small"),
                                "移動エリア": st.column_config.TextColumn("移動先", width="small"),
                                "コード": st.column_config.TextColumn("コード", width="small"),
                                "担当者": st.column_config.TextColumn("担当", width="small"),
                            }
                        )
                    else:
                        st.warning("表示可能な在庫はありません。")
        else:
            st.info("まだ有効なデータが登録されていません。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")

# フッターにQRコードを表示
st.markdown("---")
st.write("### 📝 データの入力・更新")
form_url = "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing"
qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={form_url}"

col1, col2 = st.columns([1, 2])
with col1:
    st.image(qr_api_url, caption="入力用QR", width=120)
with col2:
    st.link_button("👉 フォームを開く", form_url)
