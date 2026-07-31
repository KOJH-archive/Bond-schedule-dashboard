import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# 환경변수 로딩
load_dotenv()
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///ficc_data.db")

# 데이터 로딩 캐싱 (성능 향상)
@st.cache_data
def load_data(query: str):
    engine = create_engine(DATABASE_URI)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"DB 연결 및 데이터 조회 실패: {e}")
        return pd.DataFrame()

st.set_page_config(page_title="FICC & 저축은행 데이터 대시보드", layout="wide")

st.title("📊 FICC 채권 수급 및 저축은행 자금동향 대시보드")
st.markdown("공공데이터포털 및 한국은행 ECOS API를 통해 수집된 데이터를 조회합니다.")

st.sidebar.header("데이터 탐색")
page = st.sidebar.radio("메뉴", ["채권 발행 내역", "채권 만기 내역", "저축은행 여수신 동향"])

if page == "채권 발행 내역":
    st.subheader("📈 채권 발행 내역 (fact_bond_issuance)")
    df_issuance = load_data("SELECT * FROM fact_bond_issuance")
    
    if not df_issuance.empty:
        st.dataframe(df_issuance, use_container_width=True)
        
        st.markdown("### 채권 분류별 발행 규모 요약")
        # 수치 데이터가 올바르게 차트로 그려지도록 형변환
        df_issuance['issue_amount'] = pd.to_numeric(df_issuance['issue_amount'], errors='coerce')
        summary = df_issuance.groupby('bond_category')['issue_amount'].sum().reset_index()
        st.bar_chart(summary.set_index('bond_category'))
    else:
        st.info("데이터가 없습니다. 파이프라인을 먼저 실행해 주세요.")

elif page == "채권 만기 내역":
    st.subheader("📉 채권 만기 내역 (fact_bond_maturity)")
    df_maturity = load_data("SELECT * FROM fact_bond_maturity")
    
    if not df_maturity.empty:
        st.dataframe(df_maturity, use_container_width=True)
        
        st.markdown("### 채권 분류별 만기 규모 요약")
        df_maturity['maturity_amount'] = pd.to_numeric(df_maturity['maturity_amount'], errors='coerce')
        summary = df_maturity.groupby('bond_category')['maturity_amount'].sum().reset_index()
        st.bar_chart(summary.set_index('bond_category'))
    else:
        st.info("데이터가 없습니다. 파이프라인을 먼저 실행해 주세요.")

elif page == "저축은행 여수신 동향":
    st.subheader("🏦 저축은행 여수신 동향 (fact_savings_bank_fund)")
    df_savings = load_data("SELECT * FROM fact_savings_bank_fund")
    
    if not df_savings.empty:
        # base_month를 문자열로 유지하면서 정렬
        df_savings = df_savings.sort_values(by='base_month')
        st.dataframe(df_savings, use_container_width=True)
        
        st.markdown("### 월별 여신 및 수신 잔액 추이")
        df_savings['deposit_balance'] = pd.to_numeric(df_savings['deposit_balance'], errors='coerce')
        df_savings['loan_balance'] = pd.to_numeric(df_savings['loan_balance'], errors='coerce')
        
        chart_data = df_savings.set_index('base_month')[['deposit_balance', 'loan_balance']]
        st.line_chart(chart_data)
    else:
        st.info("데이터가 없습니다. 파이프라인을 먼저 실행해 주세요.")
