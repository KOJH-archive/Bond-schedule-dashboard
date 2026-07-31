# 📊 FICC 채권 발행·만기 및 제2금융권 자금 추이 트래커 (Bond Schedule Dashboard)

> 공공데이터포털(한국예탁결제원) 및 한국은행 ECOS API를 활용하여 특수채·시중은행채·여전채(카드/캐피탈) 발행·만기 내역과 상호저축은행 여수신 잔액 동향을 추출, 정제, 적재(ETL)하고 대시보드로 시각화하는 파이프라인 프로젝트입니다.

---

## 📌 1. 프로젝트 개요

* **프로젝트명:** 2026 H1/H2 FICC 채권 발행·만기 및 제2금융권 자금 추이 트래커
* **주요 목표:** 
  1. 외부 API(예탁결제원, 한국은행 ECOS) 연동을 통한 채권 수급 및 저축은행 여수신 잔액 자동 수집
  2. 수집된 RAW 데이터를 정제하여 SQL 데이터베이스(SQLite, PostgreSQL, MySQL 등)에 Upsert 적재
  3. 적재된 데이터를 다중 시트 엑셀(`xlsx`)로 내보내기 및 Streamlit 기반 웹 대시보드로 시각화
* **주요 기술 스택:** 
  * `Python 3.x`, `Pandas`, `NumPy`
  * `SQLAlchemy` (DB ORM & Upsert)
  * `Requests`, `xmltodict` (HTTP 통신 및 XML/JSON 하이브리드 파싱)
  * `Streamlit` (웹 대시보드 시각화)
  * `python-dotenv`, `openpyxl`

---

## 🛠 2. 프로젝트 디렉토리 및 모듈 구조

```
├── .env.example             # 환경변수 템플릿 (API 키, DB 접속 주소)
├── .gitignore               # Git 커밋 제외 설정 파일
├── requirements.txt         # 파이썬 의존성 패키지 목록
├── run.bat                  # 윈도우 원클릭 자동 실행 배치 스크립트
├── config.py                # API Key, DB URI, 타겟 발행사 고객번호 관리
├── extractor.py             # API 데이터 수집 (Pagination, 429 처리, XML/JSON 하이브리드)
├── transformer.py           # Pandas 기반 데이터 정제, 컬럼 매핑 및 날짜/수치 파싱
├── loader.py                # SQLAlchemy 기반 DB 스키마 정의 및 Upsert 적재
├── main.py                  # 전체 ETL 파이프라인 오케스트레이션 & 엑셀 추출 실행
├── app.py                   # Streamlit 대시보드 시각화 웹 애플리케이션
└── dashboard_mockup.html    # 대시보드 UI 디자인 가상 목업 (HTML/CSS/Chart.js)
```

---

## 📡 3. API 데이터 소스 및 타겟 지표

### 1) 한국예탁결제원 채권정보서비스 (공공데이터포털)
* **특수은행채:** 종류별 발행/상환 현황 조회 (`bondSecrTpNm`: '특수채')
* **시중은행채(4대):** 발행인별 채권발행내역 조회 (신한, 국민, 하나, 우리은행 `isscoCustno`)
* **여전채(카드/캐피탈):** 발행인별 채권발행내역 조회 (주요 카드사 및 캐피탈사 `isscoCustno`)

### 2) 한국은행 ECOS Open API
* **저축은행 자금동향:** 상호저축은행 수신(`1.3.3`), 상호저축은행 여신(`1.3.4`) 월별(M) 잔액 추이

---

## 🗄 4. Database 스키마 정의 (Fact Tables)

SQLAlchemy를 사용하여 DB 적재 시 테이블이 존재하지 않으면 자동으로 생성합니다.

### 1) `fact_bond_issuance` (채권 발행 내역)
| 컬럼명 | 데이터 타입 | 설명 | PK |
|---|---|---|---|
| `issue_date` | Date | 채권 발행일자 | O |
| `issuer_name` | String(255) | 발행기관명 (예: 신한은행, A카드) | O |
| `bond_category` | String(100) | 채권 분류 (시중은행채, 카드채, 캐피탈채, 특수은행채) | O |
| `issue_amount` | Numeric | 발행 금액 | |
| `coupon_rate` | Numeric | 표면 금리 (%) | |

### 2) `fact_bond_maturity` (채권 만기 내역)
| 컬럼명 | 데이터 타입 | 설명 | PK |
|---|---|---|---|
| `maturity_date` | Date | 채권 상환/만기일자 | O |
| `issuer_name` | String(255) | 발행기관명 | O |
| `bond_category` | String(100) | 채권 분류 | O |
| `maturity_amount` | Numeric | 만기 상환 예정 금액 | |

### 3) `fact_savings_bank_fund` (저축은행 여수신 동향)
| 컬럼명 | 데이터 타입 | 설명 | PK |
|---|---|---|---|
| `base_month` | String(10) | 기준년월 (YYYYMM) | O |
| `deposit_balance` | Numeric | 수신 잔액 | |
| `loan_balance` | Numeric | 여신 잔액 | |

---

## ⚡ 5. 핵심 개발 & 예외 처리 특징

1. **XML / JSON 하이브리드 파서 구현 (`extractor.py`)**
   * 예탁결제원 API가 `resultType=json` 요청을 지원하지 않고 XML로 응답할 경우를 대비하여, `json()` 파싱 실패 시 `xmltodict`로 자동 전환되어 복구되는 폴백(Fallback) 로직 탑재.
2. **발행사 고객번호 (`isscoCustno`) 기반 조회**
   * 일반 법인등록번호가 아닌 예탁결제원 내부 고유 식별 번호를 타겟팅하여 정확한 기관별 데이터를 추출.
3. **트래픽 및 에러 대응**
   * API 호출 간 0.5초 딜레이(`time.sleep`) 삽입으로 서버 부하 방지.
   * 일일 트래픽 초과(HTTP 429 Error) 시 `logging` 모듈로 기록 후 안전하게 종료하는 Graceful Shutdown 적용.
4. **DB Upsert 지원 (`loader.py`)**
   * SQLite, PostgreSQL, MySQL 등 사용하는 RDBMS Dialect에 따라 중복 키 처리(`ON CONFLICT DO UPDATE`, `ON DUPLICATE KEY UPDATE`) 자동 적용.
5. **다중 엑셀 내보내기 및 대시보드**
   * ETL 실행 완료 시 `ficc_data_export.xlsx` 파일로 자동 추출.
   * Streamlit 기반 대시보드([app.py](app.py))에서 차트 및 시각화 화면 제공.

---

## 🚀 6. 설치 및 실행 가이드 (Quick Start)

### 1) 프로젝트 클론 및 환경변수 설정
```bash
git clone https://github.com/KOJH-archive/Bond-schedule-dashboard.git
cd Bond-schedule-dashboard

# .env 파일 생성 및 API 키 설정
cp .env.example .env
```
`.env` 파일 내용 편집:
```env
PORTAL_API_KEY=발급받은_공공데이터포털_인코딩_승인키
ECOS_API_KEY=발급받은_한국은행_ECOS_API키
DATABASE_URI=sqlite:///ficc_data.db
```

### 2) 파이썬 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

### 3) ETL 파이프라인 실행 & 엑셀 추출
```bash
python main.py
```

### 4) Streamlit 대시보드 실행
```bash
streamlit run app.py
```

### 💡 (Windows 사용자 전용) 원클릭 실행
윈도우 환경에서는 `run.bat` 파일을 더블 클릭하여 의존성 설치, ETL 파이프라인 실행, Streamlit 대시보드 구동을 한 번에 자동 실행할 수 있습니다.

---

## 📝 7. 참고 사항 (Troubleshooting)

* **발행사 고객번호 획득 방법:**
  예탁결제원의 `기업정보서비스 API`를 통해 타겟 금융기관(신한, 국민, 카드사 등)의 `isscoCustno`를 조회하여 [config.py](config.py)의 `ISSUER_CUST_NUMBERS` 딕셔너리에 입력하여 사용합니다.
* **API 접근 제한 시 대안:**
  API 승인 대기 기간 중에는 [SEIBro 증권정보포털](https://seibro.or.kr) 웹사이트의 **[채권] -> [채권권리행사] -> [원리금지급일정]** 메뉴에서 동일한 데이터를 직접 엑셀로 다운로드하여 활용할 수 있습니다.
