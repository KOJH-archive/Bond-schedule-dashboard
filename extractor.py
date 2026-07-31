import requests
import time
import logging
import xmltodict
from typing import Dict, Any, List
from config import PORTAL_API_KEY, ECOS_API_KEY, PORTAL_API_URL, ECOS_API_URL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_portal_data(endpoint: str, params: Dict[str, Any]) -> List[Dict]:
    """공공데이터포털 API 공통 호출 함수 (XML/JSON 하이브리드 파싱 적용)"""
    params['serviceKey'] = PORTAL_API_KEY
    
    # JSON을 먼저 시도하지만, 메타데이터에 명시된 대로 XML 응답이 올 것에 대비
    params['resultType'] = 'json' 
    
    all_data = []
    page_no = 1
    
    while True:
        params['pageNo'] = page_no
        params['numOfRows'] = 100
        
        try:
            response = requests.get(f"{PORTAL_API_URL}/{endpoint}", params=params)
            response.raise_for_status()
            
            items = []
            total_count = 0
            
            # 1. JSON 응답인 경우
            try:
                data = response.json()
                items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
                total_count = data.get('response', {}).get('body', {}).get('totalCount', 0)
            
            # 2. XML 응답인 경우 (JSON 파싱 실패 시)
            except ValueError:
                logging.info("JSON parsing failed, attempting XML parsing (xmltodict)...")
                data_dict = xmltodict.parse(response.content)
                body = data_dict.get('response', {}).get('body', {})
                items_obj = body.get('items', {}).get('item', [])
                
                # XML 파싱 시 item이 1개일 경우 리스트가 아닌 딕셔너리로 반환되는 문제 해결
                if isinstance(items_obj, dict):
                    items = [items_obj]
                else:
                    items = items_obj
                total_count = int(body.get('totalCount', 0))
            
            if not items:
                break
                
            all_data.extend(items)
            
            if page_no * 100 >= total_count:
                break
                
            page_no += 1
            time.sleep(0.5)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data from Portal API: {e}")
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                logging.critical("API Daily Limit Exceeded. Shutting down extractor gracefully.")
                raise SystemExit("Graceful Shutdown: API Daily Limit Exceeded.")
            break
            
    return all_data

def fetch_bond_issuance_by_corp(issco_custno: str) -> List[Dict]:
    """발행인별 채권발행내역 조회 (발행사 고객번호 사용)"""
    # 메타데이터 반영: crno(법인등록번호) -> isscoCustno(발행사 고객번호)
    params = {
        'isscoCustno': issco_custno
    }
    return fetch_portal_data('getBondIssuanceList', params)
    
def fetch_special_bank_bonds() -> List[Dict]:
    """특수은행채: 종류별 발행/상환 현황 조회"""
    params = {
        'bondSecrTpNm': '특수채'
    }
    return fetch_portal_data('getBondIssuanceList', params)

def fetch_ecos_data(stat_code: str, start_month: str, end_month: str) -> List[Dict]:
    """한국은행 ECOS API 호출 함수"""
    url = f"{ECOS_API_URL}/{ECOS_API_KEY}/json/kr/1/10000/{stat_code}/M/{start_month}/{end_month}/"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'StatisticSearch' in data and 'row' in data['StatisticSearch']:
            return data['StatisticSearch']['row']
        else:
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from ECOS API: {e}")
        return []
    finally:
        time.sleep(0.5)
