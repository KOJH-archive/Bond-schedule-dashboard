import pandas as pd
import numpy as np
from typing import List, Dict

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """빈 문자열을 NaN으로 변환하여 DB의 NULL과 매핑되도록 처리"""
    df = df.replace(r'^\s*$', np.nan, regex=True)
    return df

def transform_portal_bond_data(raw_data_list: List[Dict], bond_category: str) -> pd.DataFrame:
    """공공데이터포털에서 가져온 JSON 데이터를 DataFrame으로 변환 및 정제"""
    if not raw_data_list:
        return pd.DataFrame()
        
    df = pd.DataFrame(raw_data_list)
    df['bond_category'] = bond_category
    
    # 실제 API의 응답 필드명에 맞게 매핑 수정 필요
    column_mapping = {
        'isuDt': 'issue_date',
        'corpNm': 'issuer_name',
        'isuAmt': 'issue_amount',
        'cpnRt': 'coupon_rate',
        'expDt': 'maturity_date'
    }
    df = df.rename(columns=column_mapping)
    
    expected_cols = ['issue_date', 'issuer_name', 'bond_category', 'issue_amount', 'coupon_rate', 'maturity_date']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = np.nan
            
    df = clean_data(df)
    
    # 날짜 데이터 파싱 (YYYYMMDD -> YYYY-MM-DD 형식의 Date 객체)
    if 'issue_date' in df.columns:
        df['issue_date'] = pd.to_datetime(df['issue_date'], format='%Y%m%d', errors='coerce').dt.date
    if 'maturity_date' in df.columns:
        df['maturity_date'] = pd.to_datetime(df['maturity_date'], format='%Y%m%d', errors='coerce').dt.date
        
    # 수치형 데이터 변환
    if 'issue_amount' in df.columns:
        df['issue_amount'] = pd.to_numeric(df['issue_amount'], errors='coerce')
    if 'coupon_rate' in df.columns:
        df['coupon_rate'] = pd.to_numeric(df['coupon_rate'], errors='coerce')
        
    return df

def extract_issuance_df(df: pd.DataFrame) -> pd.DataFrame:
    """발행내역 (fact_bond_issuance) DataFrame 추출"""
    cols = ['issue_date', 'issuer_name', 'bond_category', 'issue_amount', 'coupon_rate']
    if df.empty:
        return pd.DataFrame(columns=cols)
    return df[[c for c in cols if c in df.columns]].dropna(subset=['issue_date', 'issuer_name'])

def extract_maturity_df(df: pd.DataFrame) -> pd.DataFrame:
    """만기내역 (fact_bond_maturity) DataFrame 추출"""
    df_mat = df.copy()
    if 'issue_amount' in df_mat.columns:
        df_mat = df_mat.rename(columns={'issue_amount': 'maturity_amount'})
        
    cols = ['maturity_date', 'issuer_name', 'bond_category', 'maturity_amount']
    if df_mat.empty:
        return pd.DataFrame(columns=cols)
    return df_mat[[c for c in cols if c in df_mat.columns]].dropna(subset=['maturity_date', 'issuer_name'])


def transform_ecos_data(deposit_raw: List[Dict], loan_raw: List[Dict]) -> pd.DataFrame:
    """한국은행 ECOS 저축은행 동향 데이터 병합 및 정제"""
    df_deposit = pd.DataFrame(deposit_raw) if deposit_raw else pd.DataFrame(columns=['TIME', 'DATA_VALUE'])
    df_loan = pd.DataFrame(loan_raw) if loan_raw else pd.DataFrame(columns=['TIME', 'DATA_VALUE'])
    
    if not df_deposit.empty:
        df_deposit = df_deposit[['TIME', 'DATA_VALUE']].rename(columns={'TIME': 'base_month', 'DATA_VALUE': 'deposit_balance'})
        df_deposit['deposit_balance'] = pd.to_numeric(df_deposit['deposit_balance'], errors='coerce')
        
    if not df_loan.empty:
        df_loan = df_loan[['TIME', 'DATA_VALUE']].rename(columns={'TIME': 'base_month', 'DATA_VALUE': 'loan_balance'})
        df_loan['loan_balance'] = pd.to_numeric(df_loan['loan_balance'], errors='coerce')
        
    if df_deposit.empty and df_loan.empty:
        return pd.DataFrame(columns=['base_month', 'deposit_balance', 'loan_balance'])
        
    df_merged = pd.merge(df_deposit, df_loan, on='base_month', how='outer')
    df_merged = clean_data(df_merged)
    
    return df_merged
