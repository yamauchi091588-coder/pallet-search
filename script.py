import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="在庫検索アプリ")
st.title("📦 パレット在庫検索システム")

# 認証設定
@st.cache_resource
def get_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # 鍵ファイルの名前が GitHub にあるものと一文字でも違うとエラーになります
    creds = Credentials.from_service_account_file('spread-sheet-01.json', scopes=scope)
    return gspread.authorize(creds)

try:
    client = get_client()
    # スプレッドシートID
    sh = client.open_by_key('1Te1r8MmdYmq9aFTh1geSzqcbGfOtxLYejIEOU-qzxRk')
    worksheet = sh.worksheet("フォームの回答 1")
    
    st.success("スプレッドシートに正常に接続できました！")
    
    # テスト表示
    data = worksheet.get_all_values()
    st.write(f"現在のデータ件数: {len(data)}件")

except Exception as e:
    st.error(f"エラー内容: {e}")
