import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta

# アプリの基本設定
st.set_page_config(page_title="在庫検索アプリ", layout="wide")
st.title("📦 パレット在庫検索システム")

@st.cache_resource
def get_client():
    # 認証スコープの設定
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # 認証ファイルの読み込み（ご自身のファイル名に合わせてください）
    creds = Credentials.from_service_account_file('spread-sheet-01.json', scopes=scope)
    return gspread.authorize(creds)

# スプレッドシートのシリアル値を日時に変換する関数
def serial_to_datetime(serial):
    try:
        # 数字として読み込める場合のみ変換
        serial = float(serial)
        base_date = datetime(1899, 12, 30)
        return (base_date + timedelta(days=serial)).strftime('%Y/%m/%d %H:%M')
    except:
        # 数字でない（すでに文字になっているなど）場合はそのまま返す
        return str(serial)

try:
    client = get_client()
    # 修正後のスプレッドシートID
    SPREADSHEET_ID = '1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk'
    sh = client.open_by_key(SPREADSHEET_ID)
    
    # ターゲットのシート名
    worksheet = sh.worksheet("フォームの回答 1")

    # 値を計算済みの状態で取得
    all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')

    # データ抽出：5行目（index 4）から開始
    if len(all_values) >= 5:
        raw_data = all_values[4:] 
        data_list = []
        
        for row in raw_data:
            # AA列(26)からAL列(37)まである行を対象
            if len(row) > 37: 
                p_val = str(row[26]).strip() # AA列: パレット番号
                if p_val and p_val not in ["", "#N/A", "None"]:
                    data_list.append([
                        p_val,                        # パレット番号
                        serial_to_datetime(row[27]),  # AB列: 日時（変換実行）
                        str(row[29]),                 # AD列: 商品名
                        str(row[31]),                 # AF列: 元エリア
                        str(row[33]),                 # AH列: 移動エリア
                        str(row[35]),                 # AJ列: コード
                        str(row[37])                  # AL列: 担当者
                    ])
        
        # 検索用データフレームの作成
        df = pd.DataFrame(data_list, columns=["パレット番号", "日時", "商品名", "元エリア", "移動エリア", "コード", "担当者"])

        # 検索窓
        target_no = st.text_input("検索したいパレット番号を入力してください（例: 1）")

        if target_no:
            search_val = str(target_no).strip()
            
            # .0 表記などを吸収して検索
            def normalize_num(s):
                s = str(s).strip()
                if s.endswith('.0'): s = s[:-2]
                return s

            match_row = df[df["パレット番号"].apply(normalize_num) == normalize_num(search_val)]
            
            if match_row.empty:
                st.error(f"パレット番号「{search_val}」は見つかりませんでした。")
            else:
                product_name = match_row.iloc[0]["商品名"]
                st.success(f"✅ 商品名：{product_name}")

                # 同じ商品名で「工場内」を除外したリスト
                results = df[
                    (df["商品名"] == product_name) & 
                    (~df["元エリア"].str.contains("工場内", na=False)) & 
                    (~df["移動エリア"].str.contains("工場内", na=False))
                ]

                if not results.empty:
                    st.write("### 📍 在庫エリア一覧（工場内を除く）")
                    
                    # レイアウト調整：幅の指定とインデックス非表示
                    st.dataframe(
                        results, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "パレット番号": st.column_config.TextColumn("パレット番号", width="small"),
                            "日時": st.column_config.TextColumn("日時", width="medium"),
                            "元エリア": st.column_config.TextColumn("元エリア", width="small"),
                            "移動エリア": st.column_config.TextColumn("移動エリア", width="small"),
                            "コード": st.column_config.TextColumn("コード", width="small"),
                            "商品名": st.column_config.TextColumn("商品名", width="large"),
                        }
                    )
                else:
                    st.warning("表示可能な在庫（工場内以外）はありません。")
    else:
        st.error("5行目以降にデータが見つかりません。")

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.markdown("---")  # 区切り線
st.write("### 📝 データの入力・更新")

# QRコードのURL
form_url = "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing&ouid=114522078452286312724"
qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={form_url}"

# レイアウトを2列に分けて表示
col1, col2 = st.columns([1, 2])

with col1:
    st.image(qr_api_url, caption="フォーム入力用QRコード", width=200)

with col2:
    st.write("カメラで上のQRコードを読み取るか、以下のリンクからフォームを入力してください。")
    st.link_button("👉 フォームを開く（クリック）", form_url)

# --- ここまで追加 ---