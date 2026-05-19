import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import unicodedata
import re
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# 🌟 新しく文字を読み取るライブラリ(EasyOCR)をここで呼び出します
import easyocr
import numpy as np

# ページ設定
st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- 文字読み取りエンジンを準備（初回だけ少し時間がかかります） ---
@st.cache_resource
def load_ocr_reader():
    # 日英の文字を読み取れるように設定
    return easyocr.Reader(['ja', 'en'], gpu=False)

# --- サイドバー ---
st.sidebar.title("メニュー選択")
mode = st.sidebar.radio(
    "モードを選択してください", 
    ["形材検索（パレット）", "部品検索", "📷 証拠ラベル発行"]
)

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

# --- 1. 形材検索モード（維持） ---
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
                p_idx = 26
                raw_data = all_values[3:] 
                data_list = []
                for row in raw_data:
                    if len(row) > p_idx:
                        p_val = str(row[p_idx]).strip()
                        if p_val and p_val not in ["", "#N/A", "None", "nan"]:
                            honsu = str(row[p_idx+13]) if len(row) > p_idx+13 else "0"
                            moto_area = str(row[p_idx+5]).strip() if len(row) > p_idx+5 else ""
                            ido_area = str(row[p_idx+7]).strip() if len(row) > p_idx+7 else ""
                            current_loc = ido_area if ido_area and ido_area != "" else moto_area
                            data_list.append({
                                "パレット番号": p_val, "日時": serial_to_datetime(row[p_idx+1]),
                                "商品名": str(row[p_idx+3]), "本数": honsu, "現在の場所": current_loc
                            })
                df = pd.DataFrame(data_list)
                target_no = st.text_input("① パレット番号で検索")
                target_name = st.text_input("② 商品名で曖昧検索")
                if target_no:
                    search_val = super_normalize(target_no)
                    df["temp_no"] = df["パレット番号"].apply(super_normalize)
                    match_row = df[df["temp_no"] == search_val]
                    if match_row.empty:
                        st.error(f"番号「{target_no}」は見つかりませんでした。")
                    else:
                        latest = match_row.iloc[-1]
                        st.success(f"✅ パレット {target_no} は 「{latest['商品名']}」 ({latest['本数']}本)")
                        st.write(f"### 📍 場所：{latest['現在の場所']}")
                        try: st.image("IMG_1556.JPG.crdownload", use_container_width=True)
                        except: st.error("マップ画像が見つかりません。")
                elif target_name:
                    search_name = super_normalize(target_name)
                    df_temp = df.copy()
                    df_temp["temp_name"] = df_temp["商品名"].apply(super_normalize)
                    results = df_temp[df_temp["temp_name"].str.contains(search_name, na=False)]
                    if not results.empty: st.dataframe(results[["パレット番号", "商品名", "現在の場所", "本数", "日時"]].sort_index(ascending=False), use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"エラー: {e}")

# --- 2. 部品検索モード（維持） ---
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
                    if len(row) >= 5: data_list.append({"場所": row[2], "品目コード": row[3], "部品名": row[4]})
                df_parts = pd.DataFrame(data_list)
                query = st.text_input("部品名を入力してください")
                if query:
                    search_query = super_normalize(query)
                    df_parts["temp_name"] = df_parts["部品名"].apply(super_normalize)
                    results = df_parts[df_parts["temp_name"].str.contains(search_query, na=False)]
                    if not results.empty:
                        for index, row in results.iterrows():
                            with st.expander(f"📦 {row['部品名']} (場所: {row['場所']})", expanded=True):
                                clean_code = str(row['品目コード']).replace('*', '').strip()
                                bc_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={clean_code}&scale=2&rotate=N&background=ffffff&barcolor=000000"
                                st.markdown(f'<div style="background-color: white; padding: 10px; border-radius: 5px; display: inline-block;"><img src="{bc_url}"></div>', unsafe_allow_html=True)
    except Exception as e: st.error(f"エラー: {e}")

# --- 3. 📷 証拠ラベル発行モード（本番AI組み込み版） ---
elif mode == "📷 証拠ラベル発行":
    st.title("📷 はかり数値 ＆ 部品名 合成システム")
    st.write("部品箱の文字を自動で読み取り、はかりの写真と合成します。")

    # マスターデータの読み込み
    df_master = pd.DataFrame()
    try:
        client = get_client()
        if client:
            SPREADSHEET_ID = '1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk'
            sh = client.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet("部品マスター")
            all_values = worksheet.get_all_values()
            if len(all_values) > 1:
                raw_df = pd.DataFrame(all_values[1:])
                if raw_df.shape[1] >= 5:
                    df_master["場所"] = raw_df[2]
                    df_master["品目コード"] = raw_df[3]
                    df_master["部品名"] = raw_df[4]
    except:
        pass

    # 最終的に写真にスタンプする文字
    if "label_text" not in st.session_state:
        st.session_state.label_text = ""

    # --- STEP 1: 部品箱の文字読み取り ---
    st.subheader("ステップ ①：部品箱のラベルを撮影")
    box_image = st.camera_input("部品箱のコードや名前を撮影してください", key="box_cam")
    
    if box_image:
        if st.session_state.label_text == "":
            with st.spinner("🔍 写真の文字を解析中...（最初の1回目は20秒ほどかかります）"):
                try:
                    # AIエンジンを起動して文字を読み取る
                    reader = load_ocr_reader()
                    img_pil = Image.open(box_image)
                    img_np = np.array(img_pil)
                    ocr_results = reader.readtext(img_np)
                    
                    # 読み取れた文字をすべて結合
                    found_words = []
                    for res in ocr_results:
                        found_words.append(res[1])
                    
                    full_text = " ".join(found_words)
                    st.write(f"📖 読み取れた文字: `{full_text}`")
                    
                    # スプレッドシートから、読み取った文字を含む部品を探す
                    matched_code = ""
                    matched_name = ""
                    
                    if not df_master.empty:
                        for idx, row in df_master.iterrows():
                            code_clean = str(row["品目コード"]).replace('*', '').strip()
                            name_clean = str(row["部品名"]).strip()
                            
                            # 写真の中に品目コードか部品名が含まれているかチェック
                            if (code_clean and code_clean.lower() in full_text.lower()) or (name_clean and name_clean in full_text):
                                matched_code = code_clean
                                matched_name = name_clean
                                break
                    
                    # もしシートから見つかったらそれを使い、なければ写真の文字をそのまま使う
                    if matched_code:
                        st.session_state.label_text = f"CODE: {matched_code}"
                        st.success(f"🎯 部品特定成功: {matched_name} ({matched_code})")
                    else:
                        # 見つからない場合は、写真から見つかった英数字のカタマリをそのまま使う（お家テスト用）
                        # 英語・数字だけを抽出してスタンプ用に整形
                        clean_info = re.sub(r'[^a-zA-Z0-9\s-]', '', full_text).strip()
                        if clean_info:
                            st.session_state.label_text = f"INFO: {clean_info[:20]}"
                        else:
                            st.session_state.label_text = "INFO: UNKNOWN_PART"
                        st.warning(f"⚠️ マスターには未登録ですが、写真の文字 [{st.session_state.label_text}] で進めます。")
                except Exception as e:
                    st.error(f"文字スキャンエラー: {e}")
                    st.session_state.label_text = "INFO: SCAN_ERROR"

    if st.session_state.label_text:
        st.info(f"📌 現在セットされている部品情報: **{st.session_state.label_text}**")
        if st.button("🔄 箱の写真を撮り直す"):
            st.session_state.label_text = ""
            st.rerun()

    # --- STEP 2: はかりの撮影 ---
    st.subheader("ステップ ②：はかりの数値を撮影")
    scale_image = st.camera_input("「〇〇 pcs」の画面を撮影してください", key="scale_cam")

    if scale_image and st.session_state.label_text:
        st.subheader("ステップ ③：合成ラベルのプレビュー")
        
        base_img = Image.open(scale_image).convert("RGB")
        draw = ImageDraw.Draw(base_img)
        
        # 写真の最上部に黒い文字入れの帯を合成
        draw.rectangle([(0, 0), (base_img.width, 70)], fill="black")
        
        # 読み取った文字を白文字でスタンプ
        # 文字化けを100%防ぐため英数字でドカンと入れます
        draw.text((20, 20), st.session_state.label_text, fill="white")
        
        st.image(base_img, caption="この内容で印刷されます", width=400)
        
        # 印刷データへ変換
        buffered = io.BytesIO()
        base_img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # --- STEP 4: 印刷アプリへ送信 ---
        st.write("---")
        share_js = f"""
        <script>
        async function shareLabel() {{
            const blob = await (await fetch("data:image/jpeg;base64,{img_str}")).blob();
            const file = new File([blob], "label.jpg", {{ type: "image/jpeg" }});
            if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                await navigator.share({{ files: [file], title: '合成ラベル印刷' }});
            }} else {{
                alert("長押しで画像を保存して印刷アプリに渡してください。");
            }}
        }}
        </script>
        <button onclick="shareLabel()" style="
            background-color: #FF4B4B; color: white; padding: 15px; border: none; 
            border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; width: 100%;
        ">🖨️ この合成写真をプリンターに送る</button>
        """
        st.markdown(share_js, unsafe_allow_html=True)
