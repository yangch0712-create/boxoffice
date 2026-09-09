import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 제목 표시
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="어제 박스오피스 순위",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스 순위")

# -----------------------------------------------------------------------------
# 2. 날짜 계산 (한국 표준시 KST 기준 '어제')
# -----------------------------------------------------------------------------
# 배포 서버의 시계(UTC 등)와 관계없이 한국 시간(Asia/Seoul)을 기준으로 가져옵니다.
kst = pytz.timezone('Asia/Seoul')
now_kst = datetime.datetime.now(kst)
yesterday_kst = now_kst - datetime.timedelta(days=1)
target_dt = yesterday_kst.strftime("%Y%m%d")

st.caption(f"기준 일자: {yesterday_kst.strftime('%Y년 %m월 %d일')} (한국 시간 기준 자동 계산)")

# -----------------------------------------------------------------------------
# 3. KOBIS API 데이터 호출 함수 (캐싱 적용)
# -----------------------------------------------------------------------------
# ttl=3600: 같은 날짜 데이터 요청 시 1시간(3600초) 동안 API를 재호출하지 않고 캐시된 데이터를 사용합니다.
@st.cache_data(ttl=3600)
def fetch_box_office_data(api_key, date_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {
        "key": api_key,
        "targetDt": date_str
    }
    
    try:
        # API 서버에 데이터 요청
        response = requests.get(url, params=params, timeout=10)
        
        # HTTP 응답 코드가 200이 아니면 예외 발생
        if response.status_code != 200:
            return None, f"서버 응답 오류 (상태 코드: {response.status_code})"
            
        data = response.json()
        
        # 1) KOBIS 특이사항: 키가 잘못되어도 200 응답과 함께 faultInfo 상자가 들어옴
        if "faultInfo" in data:
            error_msg = data["faultInfo"].get("message", "알 수 없는 API 오류가 발생했습니다.")
            return None, f"KOBIS 오류 메시지: {error_msg}"
            
        # 2) 정상 응답 내 박스오피스 목록 추출
        box_office_result = data.get("boxOfficeResult", {})
        daily_list = box_office_result.get("dailyBoxOfficeList", [])
        
        # 3) 데이터 목록이 비어있는 경우
        if not daily_list:
            return None, "영화 목록 데이터가 비어 있습니다."
            
        return daily_list, None

    except requests.exceptions.RequestException as e:
        # 네트워크 차단, 연결 실패 등의 경우 처리
        return None, f"네트워크 통신 오류가 발생했습니다: {str(e)}"

# -----------------------------------------------------------------------------
# 4. Secrets에서 API 키 불러오기 및 예외 처리
# -----------------------------------------------------------------------------
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 API 키를 찾을 수 없습니다.")
    st.info("""
    **확인 방법:**
    1. Streamlit Cloud 앱 설정(Settings) -> **Secrets** 메뉴로 이동하세요.
    2. 아래 형식으로 KOBIS 인증키를 입력하고 저장했는지 확인하세요:
    ```toml
    KOBIS_KEY = "발급받은_인증키_입력"
    """)
    st.stop()
