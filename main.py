import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="박스오피스 분석 Dashboard", page_icon="🎬", layout="wide")

# API 설정
API_KEY = st.secrets["KOBIS_KEY"]
URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"

# 한국 시간(KST) 기준 선택 가능 최대 날짜 (어제)
KST = datetime.timezone(datetime.timedelta(hours=9))
today_kst = datetime.datetime.now(KST).date()
max_date = today_kst - datetime.timedelta(days=1)
default_start = max_date - datetime.timedelta(days=6)  # 기본 7일간의 데이터


@st.cache_data(ttl=3600)
def fetch_boxoffice(date_str):
    """KOBIS API에서 해당 날짜의 일별 박스오피스를 받아 온다."""
    params = {"key": API_KEY, "targetDt": date_str}
    res = requests.get(URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


st.title("🎬 박스오피스 분석 Dashboard")

# 1. 기간 선택 (날짜 범위 지정)
date_range = st.date_input(
    "조회할 기간을 선택하세요 (시작일 ~ 종료일)",
    value=(default_start, max_date),
    max_value=max_date,
    help="오늘 날짜는 집계 전이므로 어제 날짜까지만 선택 가능합니다."
)

# 날짜가 범위로 제대로 선택되었는지 확인
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    st.info("종료 날짜까지 선택해 주세요.")
    st.stop()

# 선택한 기간 동안의 날짜 리스트 생성
date_list = pd.date_range(start_date, end_date).tolist()

all_data = []
progress_bar = st.progress(0, text="데이터 수집 중...")

for idx, dt in enumerate(date_list):
    dt_str = dt.strftime("%Y%m%d")
    try:
        res_json = fetch_boxoffice(dt_str)
        if "faultInfo" in res_json:
            st.error(f"API 오류: {res_json['faultInfo'].get('message', '')}")
            st.stop()
        
        daily_list = res_json.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
        for m in daily_list:
            m["targetDt"] = dt.strftime("%Y-%m-%d")
            all_data.append(m)
            
    except requests.RequestException:
        st.error("서버 연결 실패. 다시 시도해 주세요.")
        st.stop()
        
    progress_bar.progress((idx + 1) / len(date_list), text=f"데이터 수집 중... ({idx+1}/{len(date_list)})")

progress_bar.empty()

if not all_data:
    st.warning("선택한 기간에는 아직 집계된 데이터가 없습니다.")
    st.stop()

df = pd.DataFrame(all_data)

# 숫자형 컬럼 변환
for col in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]:
    df[col] = pd.to_numeric(df[col])

# 순위 변동 / 100만 이모지 포맷팅 함수
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

def format_movie_name(row):
    name = row["movieNm"]
    if row["audiAcc"] >= 1000000:
        return f"{name} 🏆"
    return name

df["순위변동"] = df.apply(format_rank_inten, axis=1)
df["표시_영화명"] = df.apply(format_movie_name, axis=1)

# ==========================================
# 📌 선택한 기간의 마지막 날 기준 현황 (상단)
# ==========================================
latest_date_str = end_date.strftime("%Y-%m-%d")
latest_df = df[df["targetDt"] == latest_date_str]

if not latest_df.empty:
    top = latest_df.sort_values("rank").iloc[0]
    st.subheader(f"🥇 마지막 조회일 ({latest_date_str}) 1위 — {top['표시_영화명']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("당일 관객수", f"{top['audiCnt']:,}명")
    c2.metric("누적 관객수", f"{top['audiAcc']:,}명")
    c3.metric("스크린수", f"{top['scrnCnt']:,}개")

    st.subheader(f"📋 {latest_date_str} 박스오피스 순위표")
    table = latest_df.sort_values("rank")[["rank", "순위변동", "표시_영화명", "openDt", "audiCnt", "audiAcc", "scrnCnt"]]
    table.columns = ["순위", "전날 대비", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
    st.dataframe(table, hide_index=True, use_container_width=True)

# ==========================================
# 📊 차트 섹션
# ==========================================
st.divider()
st.header("📊 기간 종합 분석")

# 4번째 그래프: 기간 내 일관객수 합계 TOP 10 (가로 막대그래프)
st.subheader("🏆 선택 기간 총 관객수 TOP 10")

# 영화별 기간 내 총 관객수 및 10위권 진입 일수 집계
period_summary = df.groupby("movieNm").agg(
    total_audiCnt=("audiCnt", "sum"),
    days_in_top10=("rank", "count")
).reset_index()

# 관객수 기준 TOP 10 추출 (오름차순 정렬해 두어야 가로 막대에서 큰 값이 위에 위치함)
top10_period = period_summary.sort_values("total_audiCnt", ascending=True).tail(10)

fig_top10 = px.bar(
    top10_period,
    x="total_audiCnt",
    y="movieNm",
    orientation="h",
    labels={
        "total_audiCnt": "기간 총 관객수 (명)",
        "movieNm": "영화명",
        "days_in_top10": "10위권 진입 일수"
    },
    hover_data={
        "total_audiCnt": ":,명",
        "days_in_top10": ":일"
    },
    text_auto=",.0f"
)

# 관객수 많은 영화가 위에 오도록 Y축 범주 순서 고정
fig_top10.update_layout(
    yaxis={"categoryorder": "array", "categoryarray": top10_period["movieNm"].tolist()}
)

st.plotly_chart(fig_top10, use_container_width=True)
