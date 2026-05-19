import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import unicodedata
import re
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
import io
import base64
import easyocr
import numpy as np

# ページ設定
st.set_page_config(page_title="在庫管理システム", layout="wide")

# --- 文字＆QR/バーコード読み取りエンジン ---
@st.cache_resource
def load_ocr_reader():
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
    text = re.sub(r'[×*✕×✕ｘ]', 'x', text) 
    text = re.sub(r'[\s　-]', '', text)     
    return text

def serial_to_datetime(serial):
    try:
        serial = float(serial)
        base_date = datetime(1899, 12, 30)
        return (base_date + timedelta(days=serial)).strftime('%m/%d %H:%M')
    except:
        return str(serial)

# --- PDFマップを画面に埋め込んで表示する関数 ---
def display_pdf_map(pdf_filename):
    try:
        with open(pdf_filename, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except:
        st.error(f"マップファイル「{pdf_filename}」が読み込めませんでした。GitHub上のファイル名と一致しているか確認してください。")

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
                        
                        # 🎯 正しいファイル名「屋外で管理形材マップ.pdf」でマップを表示します！
                        st.write("### 🗺️ 保管エリア・マップ")
                        display_pdf_map("屋外で管理形材マップ.pdf")
                        
                elif target_name:
                    search_name = super_normalize(target_name)
                    df_temp = df.copy()
                    df_temp["temp_name"] = df_temp["商品名"].apply(super_normalize)
                    results = df_temp[df_temp["temp_name"].str.contains(search_name, na=False)]
                    if not results.empty: st.dataframe(results[["パレット番号", "商品名", "現在の場所", "本数", "日時"]].sort_index(ascending=False), use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"エラー: {e}")

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

# --- 3. 📷 証拠ラベル発行モード ---
elif mode == "📷 証拠ラベル発行":
    st.title("📷 はかり数値 ＆ 部品名 合成システム")
    st.write("部品箱の文字やコードを自動で読み取り、はかりの写真と合成します。")

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
                    df_master = pd.DataFrame()
                    df_master["場所"] = raw_df[2]
                    df_master["品目コード"] = raw_df[3]
                    df_master["部品名"] = raw_df[4]
    except:
        pass

    if "label_text" not in st.session_state: st.session_state.label_text = ""
    if "ocr_done" not in st.session_state: st.session_state.ocr_done = False
    if "candidates" not in st.session_state: st.session_state.candidates = []

    st.subheader("ステップ ①：部品箱のラベル（またはQR・バーコード）を撮影")
    box_image = st.camera_input("シールの文字やコードを撮影してください", key="box_cam")
    
    if box_image and not st.session_state.ocr_done:
        with st.spinner("🔍 画像を解析中..."):
            try:
                reader = load_ocr_reader()
                img_pil = Image.open(box_image)
                img_np = np.array(img_pil)
                ocr_results = reader.readtext(img_np)
                
                found_words = [res[1] for res in ocr_results]
                full_text = " ".join(found_words)
                normalized_full_text = super_normalize(full_text)
                
                st.write(f"📖 読み取れた文字情報: `{full_text}`")
                
                exact_match_row = None
                if not df_master.empty:
                    for idx, row in df_master.iterrows():
                        code_raw = str(row["品目コード"]).replace('*', '').strip()
                        code_norm = super_normalize(code_raw)
                        if code_norm and (code_norm in normalized_full_text):
                            exact_match_row = row
                            break
                
                if exact_match_row is not None:
                    matched_code = str(exact_match_row["品目コード"]).replace('*', '').strip()
                    st.session_state.label_text = f"CODE: {matched_code}"
                    st.success(f"🎯 コードから一発特定成功: {exact_match_row['部品名']} ({matched_code})")
                    st.session_state.ocr_done = True
                    st.session_state.candidates = []
                else:
                    candidates_list = []
                    if not df_master.empty:
                        for idx, row in df_master.iterrows():
                            code_raw = str(row["品目コード"]).replace('*', '').strip()
                            name_raw = str(row["部品名"]).strip()
                            code_norm = super_normalize(code_raw)
                            name_norm = super_normalize(name_raw)
                            
                            is_match = False
                            for word in found_words:
                                word_norm = super_normalize(word)
                                if len(word_norm) >= 3: 
                                    if (word_norm in code_norm) or (word_norm in name_norm):
                                        is_match = True
                                        break
                                        
                            if is_match:
                                if {"code": code_raw, "name": name_raw} not in candidates_list:
                                    candidates_list.append({"code": code_raw, "name": name_raw})
                    
                    st.session_state.candidates = candidates_list
                    st.session_state.ocr_done = True
                    
                    if not candidates_list:
                        clean_info = re.sub(r'[^a-zA-Z0-9\s-]', '', full_text).strip()
                        st.session_state.label_text = f"SIZE: {clean_info[:20].upper()}" if clean_info else "SIZE: 5X10 (TEST)"
                        
            except Exception as e:
                st.error(f"スキャンエラー: {e}")
                st.session_state.label_text = "INFO: ERROR"
                st.session_state.ocr_done = True

    # 候補の選択ボタン表示（25件制限）
    if st.session_state.ocr_done and st.session_state.candidates:
        if st.session_state.label_text == "":
            total_cand = len(st.session_state.candidates)
            
            if total_cand > 25:
                st.warning(f"⚠️ 候補が多すぎます（{total_cand}件）。バーコード部分、または品目コード（B00...等）を大きく写すように撮り直してください。")
                if st.button("🔄 もう一度撮り直す"):
                    st.session_state.label_text = ""
                    st.session_state.ocr_done = False
                    st.session_state.candidates = []
                    st.rerun()
            else:
                st.info(f"🎯 該当する部品候補が {total_cand} 件見つかりました。該当するものをタップしてください：")
                for cand in st.session_state.candidates:
                    if st.button(f"📦 {cand['name']} ({cand['code']})", key=f"btn_{cand['code']}"):
                        st.session_state.label_text = f"CODE: {cand['code']}"
                        st.rerun()
        else:
            st.success(f"確定した部品情報: **{st.session_state.label_text}**")

    if st.session_state.label_text:
        if st.button("🔄 箱の写真を撮り直す（クリア）"):
            st.session_state.label_text = ""
            st.session_state.ocr_done = False
            st.session_state.candidates = []
            st.rerun()

    st.subheader("ステップ ②：はかりの数値を撮影")
    scale_image = st.camera_input("「〇〇 pcs」の画面を撮影してください", key="scale_cam")

    if scale_image and st.session_state.label_text:
        st.subheader("ステップ ③：合成ラベルのプレビュー")
        
        base_img = Image.open(scale_image).convert("RGB")
        draw = ImageDraw.Draw(base_img)
        
        draw.rectangle([(0, 0), (base_img.width, 70)], fill="black")
        draw.text((20, 20), st.session_state.label_text, fill="white")
        
        st.image(base_img, caption="この内容で印刷されます", width=400)
        
        buffered = io.BytesIO()
        base_img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
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
