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
import os

# ページ設定
st.set_page_config(page_title="在庫管理システム", layout="wide")

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

# --- 🎯 PDFマップを開くボタン ---
def display_pdf_download_button_powerful():
    try:
        target_file = None
        for f in os.listdir("."):
            if "屋外" in f and "マップ" in f and f.endswith(".pdf"):
                target_file = f
                break
        if target_file and os.path.exists(target_file):
            with open(target_file, "rb") as f:
                pdf_bytes = f.read()
            st.download_button("🗺️ ここをタップしてマップ（配置図）を開く", data=pdf_bytes, file_name="屋外で管理形材マップ.pdf", mime="application/pdf", use_container_width=True)
    except:
        st.error("マップ図面ファイルが見つかりません。")

# --- 1. 形材検索モード ---
if mode == "形材検索（パレット）":
    st.title("📦 形材（パレット）在庫検索")
    st.info("💡 新しいデータを登録・修正する場合はこちらから")
    st.link_button("📤 データ入力フォームへ移動する", "https://docs.google.com/forms/d/1NNGdh6t5lmsurybephOXnERfeWl9RGZ3EyAirMS2BV0/viewform")
    st.markdown("---")
    try:
        client = get_client()
        if client:
            sh = client.open_by_key('1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk')
            worksheet = sh.worksheet("フォームの回答 1")
            all_values = worksheet.get_all_values(value_render_option='UNFORMATTED_VALUE')
            if len(all_values) >= 2:
                headers = [str(h).strip() for h in all_values[0]]
                p_idx = next((i for i, h in enumerate(headers) if "パレット番号" in h), 26)
                name_idx = next((i for i, h in enumerate(headers) if "商品名" in h or "品名" in h), p_idx+3)
                honsu_idx = next((i for i, h in enumerate(headers) if "本数" in h or "数量" in h), p_idx+13)
                moto_idx = next((i for i, h in enumerate(headers) if "元エリア" in h or "移動元" in h), p_idx+5)
                ido_idx = next((i for i, h in enumerate(headers) if "移動エリア" in h or "移動先" in h), p_idx+7)
                
                data_list = []
                for row in all_values[1:]:
                    if len(row) > p_idx:
                        p_val = str(row[p_idx]).strip()
                        if p_val and p_val not in ["", "パレット番号"]:
                            data_list.append({"パレット番号": p_val, "商品名": str(row[name_idx]), "本数": str(row[honsu_idx]), "現在の場所": str(row[ido_idx] if row[ido_idx] else row[moto_idx])})
                df = pd.DataFrame(data_list)
                target_no = st.text_input("① パレット番号で検索")
                if target_no:
                    match = df[df["パレット番号"].apply(super_normalize) == super_normalize(target_no)]
                    if not match.empty:
                        latest = match.iloc[-1]
                        st.success(f"✅ {latest['商品名']} ({latest['本数']}本) 📍 {latest['現在の場所']}")
                        display_pdf_download_button_powerful()
                    else: st.error("見つかりませんでした。")
    except Exception as e: st.error(f"エラー: {e}")

# --- 2. 部品検索モード ---
elif mode == "部品検索":
    st.title("⚙️ 部品在庫検索")
    try:
        client = get_client()
        if client:
            sh = client.open_by_key('1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk')
            worksheet = sh.worksheet("部品マスター")
            all_values = worksheet.get_all_values()
            df_parts = pd.DataFrame([{"場所": row[2], "品目コード": row[3], "部品名": row[4]} for row in all_values[1:]])
            query = st.text_input("部品名を入力してください")
            if query:
                results = df_parts[df_parts["部品名"].apply(super_normalize).str.contains(super_normalize(query), na=False)]
                for _, row in results.iterrows():
                    with st.expander(f"📦 {row['部品名']} (場所: {row['場所']})", expanded=True):
                        bc_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={str(row['品目コード']).replace('*', '')}&scale=2&background=ffffff"
                        st.markdown(f'<img src="{bc_url}">', unsafe_allow_html=True)
    except Exception as e: st.error(f"エラー: {e}")

# --- 3. 📷 証拠ラベル発行モード ---
elif mode == "📷 証拠ラベル発行":
    st.title("📷 はかり数値 ＆ 部品名 合成システム")
    input_text = st.text_input("部品コード、または部品名を入力")
    
    label_text = input_text if input_text else "部品名"
    st.subheader("ステップ ②：はかりの数値を撮影")
    scale_image = st.camera_input("「〇〇 pcs」の画面を撮影してください")

    if scale_image and label_text:
        base_img = Image.open(scale_image).convert("RGB")
        draw = ImageDraw.Draw(base_img)
        draw.rectangle([(0, 0), (base_img.width, 70)], fill="black")
        draw.text((20, 20), label_text, fill="white")
        st.image(base_img, width=400)
        
        buffered = io.BytesIO()
        base_img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        st.markdown(f'<button onclick="location.href=\'data:image/jpeg;base64,{img_str}\'" style="padding:15px; background:#FF4B4B; color:white; border:none; width:100%; border-radius:8px;">🖨️ この写真を長押しして保存</button>', unsafe_allow_html=True)
