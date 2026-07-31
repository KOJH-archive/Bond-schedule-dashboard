import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from datetime import datetime, date
from dotenv import load_dotenv

# 환경변수 로딩
load_dotenv()
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///ficc_data.db")

# 데이터 로딩 캐싱
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
st.markdown("공공데이터포털 및 한국은행 ECOS API를 통해 수집된 데이터를 조회하고 기간별 분석을 수행합니다.")

st.sidebar.header("데이터 탐색 및 조건 설정")
page = st.sidebar.radio("메뉴 선택", ["채권 만기 내역 (기간/금액별)", "채권 발행 내역", "저축은행 여수신 동향"])

# ---------------------------------------------------------
# 1. 채권 만기 내역 페이지 (기간 및 금액별 필터링 기능 강화)
# ---------------------------------------------------------
if page == "채권 만기 내역 (기간/금액별)":
    st.subheader("📉 기간별 채권 만기도래 내역 분석")
    
    df_maturity = load_data("SELECT * FROM fact_bond_maturity")
    
    if not df_maturity.empty:
        # 날짜 및 수치 데이터 형변환
        df_maturity['maturity_date'] = pd.to_datetime(df_maturity['maturity_date']).dt.date
        df_maturity['maturity_amount'] = pd.to_numeric(df_maturity['maturity_amount'], errors='coerce')
        
        # 사이드바 필터 설정
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 만기 기간 필터")
        
        # 기본값: 2026년 하반기 (2026-07-01 ~ 2026-12-31)
        default_start = date(2026, 7, 1)
        default_end = date(2026, 12, 31)
        
        min_db_date = df_maturity['maturity_date'].min() if not df_maturity['maturity_date'].isna().all() else default_start
        max_db_date = df_maturity['maturity_date'].max() if not df_maturity['maturity_date'].isna().all() else default_end
        
        date_range = st.sidebar.date_input(
            "조회 만기 기간 선택",
            value=(default_start, default_end),
            min_value=min_db_date,
            max_value=max_db_date
        )
        
        # 카테고리 필터
        categories = ["전체"] + list(df_maturity['bond_category'].dropna().unique())
        selected_category = st.sidebar.selectbox("채권 분류 선택", categories)
        
        # 정렬 필터 (금액 우선 / 날짜 우선)
        sort_option = st.sidebar.radio("정렬 기준", ["금액 큰 순서 (우선)", "만기일자 순서"])
        
        # 기간 필터링 적용
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_d, end_d = date_range
            filtered_df = df_maturity[
                (df_maturity['maturity_date'] >= start_d) & 
                (df_maturity['maturity_date'] <= end_d)
            ]
        else:
            filtered_df = df_maturity.copy()
            
        # 카테고리 필터링 적용
        if selected_category != "전체":
            filtered_df = filtered_df[filtered_df['bond_category'] == selected_category]
            
        # 정렬 적용
        if sort_option == "금액 큰 순서 (우선)":
            filtered_df = filtered_df.sort_values(by='maturity_amount', ascending=False)
        else:
            filtered_df = filtered_df.sort_values(by='maturity_date', ascending=True)
            
        # 요약 메트릭 표시
        total_amount = filtered_df['maturity_amount'].sum()
        total_count = len(filtered_df)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("조회 기간 총 만기 건수", f"{total_count:,} 건")
        col2.metric("조회 기간 총 만기 도래액", f"₩ {total_amount:,.0f} 원")
        col3.metric("조회 설정 기간", f"{start_d} ~ {end_d}")
        
        st.markdown("### 📋 만기도래 상세 리스트 (금액/기간 필터 적용)")
        st.dataframe(
            filtered_df.style.format({'maturity_amount': '{:,.0f}'}),
            use_container_width=True
        )
        
        st.markdown("### 📊 채권 분류별 만기 규모 요약")
        cat_summary = filtered_df.groupby('bond_category')['maturity_amount'].sum().reset_index()
        st.bar_chart(cat_summary.set_index('bond_category'))
        
    else:
        st.info("데이터베이스에 만기 내역 데이터가 없습니다. 먼저 파이프라인(main.py)을 실행해 주세요.")

# ---------------------------------------------------------
# 2. 채권 발행 내역 페이지
# ---------------------------------------------------------
elif page == "채권 발행 내역":
    st.subheader("📈 채권 발행 내역 (fact_bond_issuance)")
    df_issuance = load_data("SELECT * FROM fact_bond_issuance")
    
    if not df_issuance.empty:
        df_issuance['issue_date'] = pd.to_datetime(df_issuance['issue_date']).dt.date
        df_issuance['issue_amount'] = pd.to_numeric(df_issuance['issue_amount'], errors='coerce')
        
        st.dataframe(df_issuance.style.format({'issue_amount': '{:,.0f}'}), use_container_width=True)
        
        st.markdown("### 채권 분류별 발행 규모 요약")
        summary = df_issuance.groupby('bond_category')['issue_amount'].sum().reset_index()
        st.bar_chart(summary.set_index('bond_category'))
    else:
        st.info("데이터가 없습니다. 파이프라인을 먼저 실행해 주세요.")

# ---------------------------------------------------------
# 3. 저축은행 여수신 동향 페이지
# ---------------------------------------------------------
elif page == "저축은행 여수신 동향":
    st.subheader("🏦 저축은행 여수신 동향 (fact_savings_bank_fund)")
    df_savings = load_data("SELECT * FROM fact_savings_bank_fund")
    
    if not df_savings.empty:
        df_savings = df_savings.sort_values(by='base_month')
        st.dataframe(df_savings, use_container_width=True)
        
        st.markdown("### 월별 여신 및 수신 잔액 추이")
        df_savings['deposit_balance'] = pd.to_numeric(df_savings['deposit_balance'], errors='coerce')
        df_savings['loan_balance'] = pd.to_numeric(df_savings['loan_balance'], errors='coerce')
        
        chart_data = df_savings.set_index('base_month')[['deposit_balance', 'loan_balance']]
        st.line_chart(chart_data)
    else:
        st.info("데이터가 없습니다. 파이프라인을 먼저 실행해 주세요.")
