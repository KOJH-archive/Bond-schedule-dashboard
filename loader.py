import logging
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, String, Date, Numeric
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from config import DATABASE_URI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

engine = create_engine(DATABASE_URI)
metadata = MetaData()

# 테이블 스키마 정의
fact_bond_issuance = Table(
    'fact_bond_issuance', metadata,
    Column('issue_date', Date, primary_key=True),
    Column('issuer_name', String(255), primary_key=True),
    Column('bond_category', String(100), primary_key=True),
    Column('issue_amount', Numeric),
    Column('coupon_rate', Numeric)
)

fact_bond_maturity = Table(
    'fact_bond_maturity', metadata,
    Column('maturity_date', Date, primary_key=True),
    Column('issuer_name', String(255), primary_key=True),
    Column('bond_category', String(100), primary_key=True),
    Column('maturity_amount', Numeric)
)

fact_savings_bank_fund = Table(
    'fact_savings_bank_fund', metadata,
    Column('base_month', String(10), primary_key=True),
    Column('deposit_balance', Numeric),
    Column('loan_balance', Numeric)
)

def init_db():
    """테이블이 존재하지 않으면 생성"""
    metadata.create_all(engine)
    logging.info("Database tables verified (created if not exists).")

def load_data(df: pd.DataFrame, table: Table):
    """SQLAlchemy를 사용한 Upsert 방식 데이터 적재"""
    if df.empty:
        logging.info(f"No data to load for table {table.name}")
        return

    records = df.to_dict(orient='records')
    
    with engine.begin() as conn:
        dialect = engine.dialect.name
        
        if dialect == 'sqlite':
            # SQLite >= 3.24 supports ON CONFLICT
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = sqlite_insert(table).values(records)
            update_dict = {c.name: c for c in stmt.excluded if not c.primary_key}
            if update_dict:
                stmt = stmt.on_conflict_do_update(
                    index_elements=[c.name for c in table.primary_key.columns],
                    set_=update_dict
                )
            else:
                stmt = stmt.on_conflict_do_nothing()
            conn.execute(stmt)
            
        elif dialect == 'postgresql':
            stmt = pg_insert(table).values(records)
            update_dict = {c.name: c for c in stmt.excluded if not c.primary_key}
            if update_dict:
                stmt = stmt.on_conflict_do_update(
                    index_elements=[c.name for c in table.primary_key.columns],
                    set_=update_dict
                )
            else:
                stmt = stmt.on_conflict_do_nothing()
            conn.execute(stmt)
            
        elif dialect == 'mysql':
            stmt = mysql_insert(table).values(records)
            update_dict = {c.name: c for c in stmt.inserted if not c.primary_key}
            if update_dict:
                stmt = stmt.on_duplicate_key_update(**update_dict)
            conn.execute(stmt)
            
        else:
            # 기타 DB에 대해서는 append 처리 (중복키 에러 발생 가능성 있음)
            df.to_sql(table.name, con=conn, if_exists='append', index=False)
            
    logging.info(f"Successfully loaded {len(records)} records into {table.name}.")
