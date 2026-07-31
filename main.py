import logging
import pandas as pd
from config import ISSUER_CUST_NUMBERS
import extractor
import transformer
import loader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_bond_data():
    """예탁결제원 채권 데이터 ETL 워크플로우"""
    all_issuance_dfs = []
    all_maturity_dfs = []
    
    # 1. 특수은행채 조회
    logging.info("Fetching Special Bank Bonds...")
    special_raw = extractor.fetch_special_bank_bonds()
    if special_raw:
        df_transformed = transformer.transform_portal_bond_data(special_raw, '특수은행채')
        all_issuance_dfs.append(transformer.extract_issuance_df(df_transformed))
        all_maturity_dfs.append(transformer.extract_maturity_df(df_transformed))
        
    # 2. 시중은행채, 여전채(카드/캐피탈) 조회
    for category, cust_list in ISSUER_CUST_NUMBERS.items():
        logging.info(f"Fetching data for category: {category}")
        for cust_no in cust_list:
            logging.info(f"  -> Fetching for issuer customer no: {cust_no}")
            raw_data = extractor.fetch_bond_issuance_by_corp(cust_no)
            if raw_data:
                df_transformed = transformer.transform_portal_bond_data(raw_data, category)
                all_issuance_dfs.append(transformer.extract_issuance_df(df_transformed))
                all_maturity_dfs.append(transformer.extract_maturity_df(df_transformed))
                
    # 3. 데이터 병합 및 적재
    if all_issuance_dfs:
        final_issuance_df = pd.concat(all_issuance_dfs, ignore_index=True)
        loader.load_data(final_issuance_df, loader.fact_bond_issuance)
        
    if all_maturity_dfs:
        final_maturity_df = pd.concat(all_maturity_dfs, ignore_index=True)
        loader.load_data(final_maturity_df, loader.fact_bond_maturity)

def process_ecos_data():
    """한국은행 ECOS 저축은행 자금동향 ETL 워크플로우"""
    logging.info("Fetching ECOS Savings Bank Data...")
    
    # 2026 H1/H2 등 특정 기간 조회 조건
    start_month = "202601"
    end_month = "202606"
    
    deposit_raw = extractor.fetch_ecos_data("1.3.3", start_month, end_month)
    loan_raw = extractor.fetch_ecos_data("1.3.4", start_month, end_month)
    
    df_savings = transformer.transform_ecos_data(deposit_raw, loan_raw)
    loader.load_data(df_savings, loader.fact_savings_bank_fund)

def main():
    """메인 실행 진입점 (스케줄러와 연결 가능)"""
    logging.info("Starting FICC & Savings Bank Data ETL Pipeline...")
    
    # 1. DB 초기화 (스키마 생성)
    loader.init_db()
    
    # 2. 예탁결제원 데이터 프로세스
    process_bond_data()
    
    # 3. 한국은행 ECOS 데이터 프로세스
    process_ecos_data()
    
    # 4. 엑셀 파일로 추출 (Export to Excel)
    export_to_excel()
    
    logging.info("ETL Pipeline Execution Completed.")

def export_to_excel():
    """DB에 적재된 데이터를 엑셀 파일로 추출"""
    excel_filename = "ficc_data_export.xlsx"
    logging.info(f"Exporting DB data to Excel file: {excel_filename}")
    
    try:
        with loader.engine.connect() as conn:
            # Pandas의 read_sql을 통해 테이블 데이터를 바로 불러와서 엑셀 시트에 각각 씁니다.
            df_issuance = pd.read_sql("SELECT * FROM fact_bond_issuance", con=conn)
            df_maturity = pd.read_sql("SELECT * FROM fact_bond_maturity", con=conn)
            df_savings = pd.read_sql("SELECT * FROM fact_savings_bank_fund", con=conn)
            
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            df_issuance.to_excel(writer, sheet_name='채권발행내역', index=False)
            df_maturity.to_excel(writer, sheet_name='채권만기내역', index=False)
            df_savings.to_excel(writer, sheet_name='저축은행여수신', index=False)
            
        logging.info("Successfully exported data to Excel.")
    except Exception as e:
        logging.error(f"Failed to export Excel file: {e}")

if __name__ == "__main__":
    main()
