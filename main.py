import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="박스오피스 조회", page_icon="🎬", layout="wide")

# 인증키는 비밀 금고(secrets)에서 불러온다
API_KEY = st.secrets["KOBIS_KEY"]
URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"

# 한국 시간(KST) 기준 날짜 계산
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
max_date = today_kst - datetime.timedelta(days=1)  # 선택 가능한 가장 늦은 날짜 (어제)


@st.cache_data(ttl=3600)  # 같은 날짜는 한 시간 동안 캐싱
def fetch_boxoffice(date_str):
    """KOBIS API에서 해당 날짜의 일별 박스오피스를 받아 온다."""
    params = {"key": API_KEY, "targetDt": date_str}
    res = requests.get(URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


st.title("🎬 박스오피스 조회")

# 1. 달력에서 날짜를 고를 수 있도록 수정을 반영 (최대 어제까지 선택 가능)
selected_date = st.date_input(
    "조회할 날짜를 선택하세요",
    value=max_date,
    max_value=max_date,
    help="오늘 날짜는 아직 집계 전이므로 어제 날짜까지만 선택 가능합니다."
)

target_dt = selected_date.strftime("%Y%m%d")
st.caption(f"조회 날짜: {selected_date}")

try:
    data = fetch_boxoffice(target_dt)
except requests.RequestException:
    st.error("서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 잠시 뒤 새로고침해 주세요.")
    st.stop()

# 인증키 오류 처리
if "faultInfo" in data:
    st.error(f"API가 오류를 돌려주었습니다: {data['faultInfo'].get('message', '')}")
    st.info("비밀 금고(secrets)의 KOBIS_KEY 값이 올바른지 확인해 주세요.")
    st.stop()

movies = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])

# 2. 고른 날짜에 영화 목록이 비어 있을 때 안내 문구
if not movies:
    st.warning("그날은 아직 집계 전입니다.")
    st.stop()

df = pd.DataFrame(movies)

# 숫자형 컬럼 변환 (rankInten 추가)
for col in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]:
    df[col] = pd.to_numeric(df[col])

# 3. rankInten 기반 순위 증감 표시 함수
def format_rank_inten(row):
    if row.get("rankOldAndNew") == "NEW":
        return "NEW"
    
    inten = row["rankInten"]
    if inten > 0:
        return f"🔺 {inten}"
    elif inten < 0:
        return f"🔹 {abs(inten)}"
    else:
        return "-"

# 4. 누적 관객 100만 명 이상 영화에 트로피 이모지(🏆) 추가
def format_movie_name(row):
    name = row["movieNm"]
    if row["audiAcc"] >= 1000000:
        return f"{name} 🏆"
    return name

df["순위변동"] = df.apply(format_rank_inten, axis=1)
df["표시_영화명"] = df.apply(format_movie_name, axis=1)

# 1위 영화 메트릭 카드 표시
top = df.sort_values("rank").iloc[0]
st.subheader(f"🥇 1위 — {top['표시_영화명']}")
c1, c2, c3 = st.columns(3)
c1.metric("당일 관객수", f"{top['audiCnt']:,}명")
c2.metric("누적 관객수", f"{top['audiAcc']:,}명")
c3.metric("스크린수", f"{top['scrnCnt']:,}개")

# 전체 순위표
st.subheader("📋 박스오피스 순위표")
table = df.sort_values("rank")[["rank", "순위변동", "표시_영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]]
table.columns = ["순위", "전날 대비", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
st.dataframe(table, hide_index=True, use_container_width=True)

# 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 상위 5편")
top5 = df.sort_values("audiCnt", ascending=False).head(5)
fig = px.bar(
    top5, 
    x="movieNm", 
    y="audiCnt", 
    labels={"movieNm": "영화명", "audiCnt": "관객수"},
    text_auto=True
)
st.plotly_chart(fig, use_container_width=True)
