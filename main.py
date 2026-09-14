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
default_start = max_date - datetime.timedelta(days=6)  # 기본 7일간 데이터


@st.cache_data(ttl=3600)
def fetch_boxoffice(date_str):
    """KOBIS API에서 해당 날짜의 일별 박스오피스를 받아 온다."""
    params = {"key": API_KEY, "targetDt": date_str}
    res = requests.get(URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


st.title("🎬 박스오피스 분석 Dashboard")

# 1. 기간 선택 (날짜 범위 지정 - 어제까지만 선택 가능)
date_range = st.date_input(
    "조회할 기간을 선택하세요 (시작일 ~ 종료일)",
    value=(default_start, max_date),
    max_value=max_date,
    help="오늘 날짜는 집계 전이므로 어제 날짜까지만 선택 가능합니다."
)

# 날짜가 범위(시작일, 종료일)로 모두 선택되었는지 확인
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
    st.warning("그날은 아직 집계 전입니다.")
    st.stop()

df = pd.DataFrame(all_data)

# 숫자형 컬럼 변환
for col in ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]:
    df[col] = pd.to_numeric(df[col])

# 순위 변동 / 100만 이상 이모지 포맷팅 함수
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
# 📌 선택한 기간의 마지막 날 기준 현황 & 표
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
# 📊 그래프 시각화 섹션
# ==========================================
st.divider()
st.header("📊 그래프 시각화")

col1, col2 = st.columns(2)

# ------------------------------------------
# 1️⃣ 그래프: 조회 마지막 날 관객수 상위 5편
# ------------------------------------------
with col1:
    st.subheader(f"📊 {latest_date_str} 관객수 상위 5편")
    if not latest_df.empty:
        top5_latest = latest_df.sort_values("audiCnt", ascending=False).head(5)
        fig1 = px.bar(
            top5_latest,
            x="movieNm",
            y="audiCnt",
            labels={"movieNm": "영화명", "audiCnt": "당일 관객수"},
            text_auto=",.0f"
        )
        st.plotly_chart(fig1, use_container_width=True)

# ------------------------------------------
# 2️⃣ 그래프: 주요 영화 일별 관객수 추이
# ------------------------------------------
with col2:
    st.subheader("📈 기간 내 일별 관객수 추이 (상위 5편)")
    # 기간 내 총 관객수가 많은 상위 5개 영화 선택
    top5_movies = df.groupby("movieNm")["audiCnt"].sum().nlargest(5).index
    df_top5_trend = df[df["movieNm"].isin(top5_movies)]
    
    fig2 = px.line(
        df_top5_trend,
        x="targetDt",
        y="audiCnt",
        color="movieNm",
        labels={"targetDt": "날짜", "audiCnt": "일별 관객수", "movieNm": "영화명"},
        markers=True
    )
    st.plotly_chart(fig2, use_container_width=True)

col3, col4 = st.columns(2)

# ------------------------------------------
# 3️⃣ 그래프: 관객수 vs 스크린수 관계 (점그래프)
# ------------------------------------------
with col3:
    st.subheader("🎯 스크린수 대비 관객수 분포")
    fig3 = px.scatter(
        latest_df,
        x="scrnCnt",
        y="audiCnt",
        color="movieNm",
        size="audiAcc",
        hover_name="movieNm",
        labels={"scrnCnt": "스크린수", "audiCnt": "당일 관객수", "movieNm": "영화명", "audiAcc": "누적 관객수"}
    )
    st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------
# 4️⃣ 그래프: 기간 내 총 관객수 TOP 10 (가로 막대그래프)
# ------------------------------------------
with col4:
    st.subheader("🏆 선택 기간 총 관객수 TOP 10")

    # 영화별 기간 내 총 관객수 및 10위권 진입 일수 집계
    period_summary = df.groupby("movieNm").agg(
        total_audiCnt=("audiCnt", "sum"),
        days_in_top10=("rank", "count")
    ).reset_index()

    # 관객수 기준 TOP 10 추출 (오름차순 정렬 - 가로 막대 시 큰 값이 위에 배치됨)
    top10_period = period_summary.sort_values("total_audiCnt", ascending=True).tail(10)

    fig4 = px.bar(
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

    # 관객수가 많은 영화가 맨 위에 배치되도록 Y축 순서 설정
    fig4.update_layout(
        yaxis={"categoryorder": "array", "categoryarray": top10_period["movieNm"].tolist()}
    )

    st.plotly_chart(fig4, use_container_width=True)
