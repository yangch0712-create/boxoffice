import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="영화 데이터 그래프 도감 1 - 시간",
    page_icon="🎬",
    layout="wide"
)

# 2. 메인 타이틀
st.title("🎬 영화 데이터 그래프 도감 1 - 시간")
st.markdown("1년치(365일) 일별 박스오피스 데이터를 바탕으로 시간 흐름에 따른 시각화 그래프를 제공합니다.")
st.markdown("---")

# 3. 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_daily.csv"
    df = pd.read_csv(url)
    
    # '날짜' 열을 문자열 변환 후 datetime 객체로 변환 (YYYYMMDD -> YYYY-MM-DD)
    df['날짜'] = pd.to_datetime(df['날짜'].astype(str), format='%Y%m%d')
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# ==========================================
# [섹션 1] 영화별 일관객수 변화 (선 그래프)
# ==========================================
st.subheader("1. 영화별 일관객수 추이")

# 영화 목록 추출 (가나다순 정렬)
movie_list = sorted(df['영화명'].unique())

# 영화 선택 드롭다운
selected_movie = st.selectbox(
    "📊 관객수 추이를 확인할 영화를 선택하세요:",
    movie_list,
    index=0
)

# 선택한 영화 데이터 필터링 및 날짜순 정렬
filtered_df = df[df['영화명'] == selected_movie].sort_values('날짜')

# Plotly 선 그래프 생성
fig1 = px.line(
    filtered_df,
    x='날짜',
    y='일관객',
    title=f"<{selected_movie}> 날짜별 일관객수 변화",
    labels={'날짜': '날짜', '일관객': '일일 관객수(명)'},
    hover_data={'날짜': '|%Y-%m-%d', '일관객': ':,d'}
)

# 그래프 디자인 요소 설정
fig1.update_traces(mode='lines+markers', line=dict(width=2.5))
fig1.update_layout(
    xaxis_title="날짜",
    yaxis_title="일일 관객수(명)",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=50, b=20)
)

# Plotly 그래프 출력
st.plotly_chart(fig1, use_container_width=True)

# 그래프 해설 문구 자리
st.info("💡 **원하는 영화의 개봉 이후 시간의 흐름에 따른 관객수의 변화와 주말과 평일 간 그 관객수 차이의 폭이 특히 두드러지게 나타난다는 것을 확인할 수 있다.")

st.markdown("---")

# ==========================================
# [섹션 2] 상위 Top 5 영화의 개봉일차별 일관객수 비교 (가로축: 개봉일차)
# ==========================================
st.subheader("2. 일관객 합계 Top 5 영화의 개봉일차별 일관객수 비교")

# 전체 기간 동안 일관객 합계 상위 5개 영화 추출
top5_movies = (
    df.groupby('영화명')['일관객']
    .sum()
    .nlargest(5)
    .index.tolist()
)

# Top 5 영화 데이터 필터링
top5_df = df[df['영화명'].isin(top5_movies)].copy()

# 각 영화별 최초 등재 날짜(개봉일) 기준 '개봉일차' 로직 계산
top5_df['최초날짜'] = top5_df.groupby('영화명')['날짜'].transform('min')
top5_df['개봉일차'] = (top5_df['날짜'] - top5_df['최초날짜']).dt.days + 1

# 개봉일차 기준으로 정렬
top5_df = top5_df.sort_values(['영화명', '개봉일차'])

# Plotly 복수 선 그래프 생성 (x축: 개봉일차)
fig2 = px.line(
    top5_df,
    x='개봉일차',
    y='일관객',
    color='영화명',
    title="기간 내 일관객 합계 Top 5 영화의 개봉일차별 일관객수 비교",
    labels={'개봉일차': '개봉일차 (일)', '일관객': '일일 관객수(명)', '영화명': '영화 제목'},
    hover_data={'날짜': '|%Y-%m-%d', '개봉일차': '%d일차', '일관객': ':,d'}
)

fig2.update_traces(mode='lines+markers')
fig2.update_layout(
    xaxis_title="개봉일차 (1일차 = 차트에 진입한 첫날)",
    yaxis_title="일일 관객수(명)",
    hovermode="x unified",
    legend_title_text="영화 선택 (범례 클릭 시 토글)",
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig2, use_container_width=True)

# 그래프 해설 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** 가로 x축을 개봉일차, 즉 차트에 집계하기 시작한 첫날로 계산함으로써 개봉 시기가 서로 다른 흥행작들의 관객이 얼마나 되는지 볼 수 있다. 그리고 영화의 흥행이 어디까지 지속되는지 그래프의 가로 x축 길이에 따라 확인할 수 있다.")

st.markdown("---")

# ==========================================
# [섹션 3] 날짜별 박스오피스 10위권 총관객수 추이 (영역 그래프)
# ==========================================
st.subheader("3. 날짜별 박스오피스 10위권 총관객수 추이")

# 날짜별 10위권 일관객 합계 계산
daily_total_df = df.groupby('날짜')['일관객'].sum().reset_index()
daily_total_df = daily_total_df.sort_values('날짜')

# 영역 그래프(Area Chart) 생성
fig3 = px.area(
    daily_total_df,
    x='날짜',
    y='일관객',
    title="일별 박스오피스 Top 10 관객 총합계 (전체 극장가 활성도)",
    labels={'날짜': '날짜', '일관객': '10위권 일관객 총합계(명)'},
    hover_data={'날짜': '|%Y-%m-%d', '일관객': ':,d'}
)

# 관객 합계가 가장 컸던 상위 3일 추출
top3_days = daily_total_df.nlargest(3, '일관객')

# 그래프 스타일 및 피크데이 텍스트/마커 추가
fig3.update_traces(line=dict(width=1.5, color='#1f77b4'), fillcolor='rgba(31, 119, 180, 0.3)')

for idx, row in top3_days.iterrows():
    date_str = row['날짜'].strftime('%Y-%m-%d')
    audience_count = f"{row['일관객']:,}명"
    rank = top3_days.index.get_loc(idx) + 1
    
    fig3.add_annotation(
        x=row['날짜'],
        y=row['일관객'],
        text=f"🏆 Top {rank}<br>{date_str}<br>({audience_count})",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1.5,
        arrowcolor="#d62728",
        ax=0,
        ay=-45,
        bordercolor="#d62728",
        borderwidth=1,
        borderpad=4,
        bgcolor="#ffffff",
        opacity=0.9,
        font=dict(size=11, color="#d62728")
    )

fig3.update_layout(
    xaxis_title="날짜",
    yaxis_title="10위권 일관객 총합계(명)",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig3, use_container_width=True)

# 그래프 해설 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** 그래프를 일년 단위로 보는 것으로써 극장에 관객이 언제 가장 몰리는지를 확인할 수 있었다. 1등은 작년 크리스마스인 12월 25일, 2등은 가려져서 방학이 끝나기 전주 주말에 해당하는 올해 8월 9일, 3등 또한 마지막 여름방학을 즐기기 위한 학생들이 발악이었던 것으로 확인된다.")

st.markdown("---")

# ==========================================
# [섹션 4] 기간 내 일관객 합계 Top 10 영화 (가로 막대그래프)
# ==========================================
st.subheader("4. 기간 내 일관객 합계 Top 10 영화")

# 영화별 일관객 합계 및 10위권 진입 일수 집계
top10_aggregated = (
    df.groupby('영화명')
    .agg(
        총일관객=('일관객', 'sum'),
        진입일수=('날짜', 'nunique')
    )
    .reset_index()
)

# 상위 10개 영화 추출 및 정렬
top10_movies_df = top10_aggregated.nlargest(10, '총일관객').copy()

# Plotly 가로 막대그래프 생성
fig4 = px.bar(
    top10_movies_df,
    x='총일관객',
    y='영화명',
    orientation='h',
    title="기간 내 일관객 합계 Top 10 영화",
    labels={'총일관객': '기간 내 일관객 합계(명)', '영화명': '영화 제목', '진입일수': '10위권 등재 일수'},
    hover_data={
        '총일관객': ':,d',
        '진입일수': ':%d일',
        '영화명': True
    },
    text_auto=',d', # 막대 끝에 숫자 표시
    color='총일관객',
    color_continuous_scale='Blues'
)

fig4.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    xaxis_title="기간 내 일관객 합계(명)",
    yaxis_title="영화 제목",
    coloraxis_showscale=False,
    margin=dict(l=20, r=20, t=50, b=20)
)

fig4.update_traces(
    textposition='outside',
    cliponaxis=False
)

st.plotly_chart(fig4, use_container_width=True)

# 그래프 해설 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** 해당 기간 동안 전체 박스오피스를 주도한 최상위 흥행작 10편의 관객 규모와 박스오피스 Top 10에 머무른 유지 기간(롱런 여부)을 함께 비교해볼 수 있습니다.")

st.markdown("---")

# ==========================================
# [섹션 5] 월×요일별 일관객 합계 히트맵 (신규 추가)
# ==========================================
st.subheader("5. 월×요일별 일관객 합계 히트맵")

# 날짜 데이터에서 월과 요일 추출
heatmap_df = df.copy()
heatmap_df['월'] = heatmap_df['날짜'].dt.month.astype(str) + "월"

# 요일 매핑 및 순서 지정 (월요일 ~ 일요일)
days_order = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
day_map = {0: '월요일', 1: '화요일', 2: '수요일', 3: '목요일', 4: '금요일', 5: '토요일', 6: '일요일'}
heatmap_df['요일'] = heatmap_df['날짜'].dt.dayofweek.map(day_map)

# 월 순서 설정 (1월 ~ 12월)
months_order = [f"{i}월" for i in range(1, 13)]

# 월 x 요일별 일관객 합계 피벗 테이블 작성
pivot_df = heatmap_df.groupby(['월', '요일'])['일관객'].sum().reset_index()
pivot_matrix = pivot_df.pivot(index='월', columns='요일', values='일관객')

# 월 및 요일 순서에 맞춰 데이터 재배치
pivot_matrix = pivot_matrix.reindex(
    index=[m for m in months_order if m in pivot_matrix.index],
    columns=days_order
)

# Plotly 히트맵 생성
fig5 = px.imshow(
    pivot_matrix,
    labels=dict(x="요일", y="월", color="일관객 합계(명)"),
    x=pivot_matrix.columns,
    y=pivot_matrix.index,
    color_continuous_scale="Reds",  # 관객수가 많을수록 진한 색상 표시
    title="월×요일별 관객 동원 분포 (히트맵)",
    text_auto=',d'  # 각 셀 내부 관객수 숫자 표기
)

fig5.update_layout(
    xaxis_title="요일",
    yaxis_title="월",
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig5, use_container_width=True)

# 그래프 해설 문구 자리
st.info("💡 **이 그래프로 알 수 있는 것:** 연중 어떤 월의 무슨 요일에 극장 관객 몰림 현상이 가장 심했는지, 주말 대비 평일 관객 비중과 계절성 관객 패턴을 입체적으로 파악할 수 있습니다.")

st.markdown("---")

# ==========================================
# [섹션 6] (추가 예정 구역)
# ==========================================
st.subheader("6. (추가 예정 구역)")
st.caption("📌 이 구역에는 추가 분석 그래프가 배치될 예정입니다.")
