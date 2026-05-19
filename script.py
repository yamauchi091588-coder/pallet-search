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

st.set_page_config(page_title="在庫管理システム", layout="wide")

def super_normalize(text):
    text = unicodedata.normalize('NFKC', str(text)).lower()
    text = re.sub(r'[×*✕×✕ｘ]', 'x', text) 
    text = re.sub(r'[\s　-]', '', text)     
    return text

@st.cache_resource
def get_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    return gspread.authorize(Credentials.from_service_account_file('spread-sheet-01.json', scopes=scope))

mode = st.sidebar.radio("モードを選択", ["形材検索", "部品検索", "📷 証拠ラベル発行"])

# 共通シート接続
client = get_client()

# --- 1. 形材検索 ---
if mode == "形材検索":
    st.title("📦 形材（パレット）検索")
    st.link_button("📤 データ入力フォーム", "https://docs.google.com/forms/d/1NNGdh6t5lmsurybephOXnERfeWl9RGZ3EyAirMS2BV0/viewform")
    sh = client.open_by_key('1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk')
    ws = sh.worksheet("フォームの回答 1")
    data = ws.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    
    q_no = st.text_input("パレット番号で検索")
    q_name = st.text_input("商品名で曖昧検索")
    
    if q_no:
        match = df[df["パレット番号"].apply(super_normalize) == super_normalize(q_no)]
        if not match.empty:
            st.success(f"{match.iloc[-1]['商品名']} ({match.iloc[-1]['本数']}本) 📍 {match.iloc[-1]['移動先'] if match.iloc[-1]['移動先'] else match.iloc[-1]['元エリア']}")
    elif q_name:
        results = df[df["商品名"].apply(super_normalize).str.contains(super_normalize(q_name), na=False)]
        if not results.empty: st.dataframe(results, use_container_width=True)

# --- 2. 部品検索 ---
elif mode == "部品検索":
    st.title("⚙️ 部品在庫検索")
    ws = client.open_by_key('1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk').worksheet("部品マスター")
    df = pd.DataFrame(ws.get_all_values()[1:], columns=["場所", "品目コード", "部品名", "他", "他2"])
    query = st.text_input("部品名を入力")
    if query:
        res = df[df["部品名"].apply(super_normalize).str.contains(super_normalize(query), na=False)]
        for _, r in res.iterrows():
            with st.expander(f"{r['部品名']} (場所: {r['場所']})"):
                # ★バーコードを白地×黒色で固定！
                bc_url = f"https://bwipjs-api.metafloor.com/?bcid=code128&text={r['品目コード'].replace('*','')}&scale=2&background=ffffff&barcolor=000000"
                st.markdown(f'<img src="{bc_url}">', unsafe_allow_html=True)

# --- 3. 証拠ラベル発行 ---
elif mode == "📷 証拠ラベル発行":
    st.title("📷 証拠写真ラベル発行")
    name = st.text_input("部品名を入力")
    img = st.camera_input("はかりを撮影")
    if img and name:
        base = Image.open(img).convert("RGB")
        draw = ImageDraw.Draw(base)
        draw.rectangle([(0,0), (base.width, 70)], fill="black")
        draw.text((20, 20), name, fill="white")
        st.image(base, width=400)
