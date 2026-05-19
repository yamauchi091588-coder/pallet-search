import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import unicodedata
import re
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- サイドバー ---
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

def super_normalize(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', str(text)).lower()
    text = re.sub(r'[×*✕]', 'x', text)
    text = re.sub(r'[\s　]', '', text)
    return text

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
                            moto_area = str(row[p_idx+5]).strip() if len(row) > p_idx+5 else ""
                            ido_area = str(row[p_idx+7]).strip() if len(row) > p_idx+7 else ""
                            
                            if ido_area and ido_area != "":
                                current_loc = ido_area
                            else:
                                current_loc = moto_area

                            data_list.append({
                                "パレット番号": p_val,
                                "日時": serial_to_datetime(row[p_idx+1]) if len(row) > p_idx+1 else "",
                                "商品名": str(row[p_idx+3]) if len(row) > p_idx+3 else "",
                                "本数": honsu,
                                "現在の場所": current_loc
                            })
                df = pd.DataFrame(data_list)
                
                st.write("### 🔍 在庫を探す")
                col1, col2 = st.columns(2)
                with col1:
                    target_no = st.text_input("① パレット番号で検索")
                with col2:
                    target_name = st.text_input("② 商品名で曖昧検索")

                if target_no:
                    search_val = super_normalize(target_no)
                    df["temp_no"] = df["パレット番号"].apply(super_normalize)
                    match_row = df[df["temp_no"] == search_val]
                    
                    if match_row.empty:
                        st.error(f"番号「{target_no}」は見つかりませんでした。")
                    else:
                        latest = match_row.iloc[-1]
                        p_name = latest["商品名"]
                        loc = latest['現在の場所']
                        
                        is_inside = "工場内" in loc

                        if is_inside:
                            st.warning(f"⚠️ パレット {target_no} は現在 【工場内】 です")
                        else:
                            st.success(f"✅ パレット {target_no} は 「{p_name}」 ({latest['本数']}本)")
                        
                        st.write(f"### 📍 場所：{loc}")
                        
                        try:
                            # レイアウト図面を最大サイズで表示
                            st.image(
                                "IMG_1556.JPG.crdownload", 
                                caption="第二工場レイアウト",
                                use_container_width=True
                            )
                        except:
                            st.error("マップ画像が見つかりません。")

                        st.write("---")
                        st.write(f"📍 **{target_no} の移動履歴**")
                        st.dataframe(match_row[["日時", "現在の場所", "本数"]].sort_index(ascending=False), use_container_width=True, hide_index=True)

                elif target_name:
                    search_name = super_normalize(target_name)
                    df_temp = df.copy()
                    df_temp["temp_name"] = df_temp["商品名"].apply(super_normalize)
                    results = df_temp[df_temp["temp_name"].str.contains(search_name, na=False)]
                    if results.empty:
                        st.warning(f"「{target_name}」は見つかりませんでした。")
                    else:
                        st.success(f"✅ {len(results)} 件見つかりました")
                        st.dataframe(results[["パレット番号", "商品名", "現在の場所", "本数", "日時"]].sort_index(ascending=False), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.link_button("👉 形材移動の入力（フォーム）", "https://docs.google.com/forms/d/e/1FAIpQLSelaDMBj0krLob-ASucKi6f4VvL70L5NmlGw8ZlVL5CEUTk8A/viewform?usp=sharing")
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
                        data_list.append({"場所": row[2], "品目コード": row[3], "部品名": row[4]})
                df_parts = pd.DataFrame(data_list)
                query = st.text_input("部品名を入力してください", key="parts_search_vfinal")
                if query:
                    search_query = super_normalize(query)
                    df_parts["temp_name"] = df_parts["部品名"].apply(super_normalize)
                    results = df_parts[df_parts["temp_name"].str.contains(search_query, na=False)]
                    if not results.empty:
                        for index, row in results.iterrows():
                            with st.expander(f"📦 {row['部品名']} (場所: {row['場所']})"):
                                st.write(f"🔢 品目コード: `{row['品目コード']}`")
                                
                                # 💡 カッコ対策の重要ポイント：
                                # 数式の "*" を取り除き、純粋なデータだけでバーコードを作成
                                raw_code = str(row['品目コード'])
                                clean_code = raw_code.replace('*', '').strip()
                                
                                # バーコード生成（背景白、バー黒）
                                bc_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={clean_code}&scale=2&rotate=N&background=ffffff&barcolor=000000"
                                
                                # ダークモードでも見やすいように白い枠を表示
                                st.markdown(
                                    f'<div style="background-color: white; padding: 10px; border-radius: 5px; display: inline-block;">'
                                    f'<img src="{bc_url}">'
                                    f'</div>', 
                                    unsafe_allow_html=True
                                )
                    else:
                        st.warning("見つかりませんでした。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
