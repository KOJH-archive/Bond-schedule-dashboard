import os
from dotenv import load_dotenv

# 환경변수 로딩
load_dotenv()

# API Keys
PORTAL_API_KEY = os.getenv("PORTAL_API_KEY", "")
ECOS_API_KEY = os.getenv("ECOS_API_KEY", "")

# Database URI
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///ficc_data.db")

# 타겟 발행사 고객번호 딕셔너리 (메타데이터 반영: 법인등록번호가 아닌 예탁원 자체 고유번호)
# '기업정보서비스' API를 통해 사전에 획득해야 하는 번호입니다.
# (현재는 테스트용 Dummy 값 배치)
ISSUER_CUST_NUMBERS = {
    "시중은행채": [
        "CUST001",  # 신한은행 (가상 고객번호)
        "CUST002",  # 국민은행 (가상 고객번호)
        "CUST003",  # 하나은행 (가상 고객번호)
        "CUST004",  # 우리은행 (가상 고객번호)
    ],
    "카드채": [
        "CUST011",  # A카드 (가상 고객번호)
        "CUST012",  # B카드 (가상 고객번호)
    ],
    "캐피탈채": [
        "CUST021",  # A캐피탈 (가상 고객번호)
        "CUST022",  # B캐피탈 (가상 고객번호)
    ]
}

# API Endpoints
PORTAL_API_URL = "http://apis.data.go.kr/1160100/service/GetBondIssuanceInfoService"
ECOS_API_URL = "http://ecos.bok.or.kr/api/StatisticSearch"
