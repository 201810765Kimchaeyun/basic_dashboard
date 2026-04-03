import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from io import StringIO

# 페이지 설정
st.set_page_config(
    page_title="Basic 요금제 코호트 분석",
    page_icon="📊",
    layout="wide"
)

# Google Sheets URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/14fhIZadKmD9r6JIY11n-OdDg47BH9vStywFRhGMM0gk/export?format=csv&gid=0"

# 색상 정의
COLORS = {
    'retain': '#10b981',
    'upgrade': '#f59e0b',
    'churn': '#ef4444',
    'pending': '#94a3b8',
    'downgrade': '#3b82f6'
}

# 티어 정의
TIERS = {
    'tier1': ['US', 'CA', 'AU', 'GB', 'NZ'],
    'tier2': ['ID', 'PH', 'TH', 'MY', 'SG'],
    'tier3': ['IN', 'VN']
}

TIER_NAMES = {
    'tier1': '1티어',
    'tier2': '2티어',
    'tier3': '3티어',
    'others': 'Others'
}

# 국가 코드 한글 매핑
COUNTRY_NAMES_KR = {
    # Tier 1
    'US': '미국', 'CA': '캐나다', 'AU': '호주', 'GB': '영국', 'NZ': '뉴질랜드',
    # Tier 2
    'ID': '인도네시아', 'PH': '필리핀', 'TH': '태국', 'MY': '말레이시아', 'SG': '싱가포르',
    # Tier 3
    'IN': '인도', 'VN': '베트남',
    # 아시아
    'KR': '대한민국', 'JP': '일본', 'CN': '중국', 'TW': '대만', 'HK': '홍콩',
    'BD': '방글라데시', 'PK': '파키스탄', 'LK': '스리랑카', 'MM': '미얀마', 'KH': '캄보디아',
    'LA': '라오스', 'MN': '몽골', 'NP': '네팔', 'BT': '부탄', 'MV': '몰디브',
    # 유럽
    'DE': '독일', 'FR': '프랑스', 'IT': '이탈리아', 'ES': '스페인', 'NL': '네덜란드',
    'BE': '벨기에', 'CH': '스위스', 'AT': '오스트리아', 'SE': '스웨덴', 'NO': '노르웨이',
    'DK': '덴마크', 'FI': '핀란드', 'PL': '폴란드', 'PT': '포르투갈', 'GR': '그리스',
    'CZ': '체코', 'HU': '헝가리', 'RO': '루마니아', 'UA': '우크라이나', 'IE': '아일랜드',
    # 북미/중남미
    'MX': '멕시코', 'BR': '브라질', 'AR': '아르헨티나', 'CL': '칠레', 'CO': '콜롬비아',
    'PE': '페루', 'VE': '베네수엘라', 'EC': '에콰도르', 'GT': '과테말라', 'CU': '쿠바',
    'BO': '볼리비아', 'DO': '도미니카공화국', 'HN': '온두라스', 'PY': '파라과이', 'SV': '엘살바도르',
    'NI': '니카라과', 'CR': '코스타리카', 'PA': '파나마', 'UY': '우루과이',
    # 중동
    'AE': '아랍에미리트', 'SA': '사우디아라비아', 'TR': '터키', 'IL': '이스라엘', 'IQ': '이라크',
    'IR': '이란', 'JO': '요르단', 'KW': '쿠웨이트', 'LB': '레바논', 'OM': '오만',
    'QA': '카타르', 'BH': '바레인', 'YE': '예멘', 'SY': '시리아',
    # 아프리카
    'ZA': '남아프리카공화국', 'EG': '이집트', 'NG': '나이지리아', 'KE': '케냐', 'GH': '가나',
    'ET': '에티오피아', 'TZ': '탄자니아', 'UG': '우간다', 'DZ': '알제리', 'MA': '모로코',
    'AO': '앙골라', 'SD': '수단', 'MZ': '모잠비크', 'MG': '마다가스카르', 'CM': '카메룬',
    'CI': '코트디부아르', 'NE': '니제르', 'BF': '부르키나파소', 'ML': '말리', 'MW': '말라위',
    'ZM': '잠비아', 'ZW': '짐바브웨', 'SN': '세네갈', 'SO': '소말리아', 'TD': '차드',
    'GN': '기니', 'RW': '르완다', 'BJ': '베냉', 'TN': '튀니지', 'BI': '부룬디',
    'SS': '남수단', 'TG': '토고', 'SL': '시에라리온', 'LY': '리비아', 'LR': '라이베리아',
    'MR': '모리타니', 'CF': '중앙아프리카공화국', 'ER': '에리트레아', 'GM': '감비아',
    # 오세아니아
    'PG': '파푸아뉴기니', 'FJ': '피지', 'NC': '뉴칼레도니아', 'PF': '프랑스령 폴리네시아',
    # 기타
    'RU': '러시아', 'BY': '벨라루스', 'KZ': '카자흐스탄', 'UZ': '우즈베키스탄', 'GE': '조지아',
    'AM': '아르메니아', 'AZ': '아제르바이잔', 'KG': '키르기스스탄', 'TJ': '타지키스탄', 'TM': '투르크메니스탄'
}

def get_country_name_kr(country_code):
    """국가 코드를 한글명으로 변환"""
    if country_code in COUNTRY_NAMES_KR:
        return f"{COUNTRY_NAMES_KR[country_code]} ({country_code})"
    return f"{country_code}"

def get_tier(country):
    for tier, countries in TIERS.items():
        if country in countries:
            return TIER_NAMES[tier]
    return TIER_NAMES['others']

@st.cache_data(ttl=300)  # 5분 캐시
def load_data():
    """Google Sheets에서 데이터 로드"""
    try:
        response = requests.get(SHEET_URL)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text))
        
        # 컬럼명 매핑
        column_mapping = {
            'idx': 'idx', 'mem_no': 'idx',
            'country': 'country', 'iso_country': 'country',
            'product': 'product', 'product_no': 'product',
            'first': 'first', 'flag_first': 'first',
            'create': 'create', 'reg_dt': 'create'
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # 날짜 파싱
        df['create'] = pd.to_datetime(df['create'])
        
        # 티어 추가
        df['tier'] = df['country'].apply(get_tier)
        
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None

def analyze_cohorts(df_full, df_cohort=None):
    """
    코호트 분석 - HTML 버전과 동일한 로직
    
    Args:
        df_full: 전체 데이터 (재결제 확인용)
        df_cohort: 코호트 대상 데이터 (None이면 df_full 사용)
    """
    if df_cohort is None:
        df_cohort = df_full
    
    today = pd.Timestamp.now().normalize()
    
    # Basic(product=9) 결제만 필터링 (코호트 대상)
    basic_data = df_cohort[df_cohort['product'] == 9].copy()
    
    # 코호트별 그룹핑 (Basic 결제일 기준)
    basic_data['cohort_date'] = basic_data['create'].dt.date
    cohorts = basic_data.groupby('cohort_date')['idx'].apply(set).to_dict()
    
    results = []
    
    for cohort_date, members in cohorts.items():
        cohort_date_obj = pd.Timestamp(cohort_date)
        expiry_date = cohort_date_obj + pd.Timedelta(days=30)
        renewable = today > expiry_date
        
        initial_users = len(members)
        retain = 0
        upgrade = 0
        churn = 0
        
        if renewable:
            for member_id in members:
                # 재결제 확인은 전체 데이터에서
                member_payments = df_full[df_full['idx'] == member_id].sort_values('create')
                after_expiry = member_payments[member_payments['create'] > expiry_date]
                
                if len(after_expiry) == 0:
                    churn += 1
                else:
                    first_renewal = after_expiry.iloc[0]
                    if first_renewal['product'] == 9:
                        retain += 1
                    elif first_renewal['product'] in [2, 6, 8]:
                        upgrade += 1
                    else:
                        churn += 1
        
        total = retain + upgrade + churn
        
        results.append({
            'cohort_date': str(cohort_date),
            'initial_users': int(initial_users),
            'retain': int(retain),
            'upgrade': int(upgrade),
            'churn': int(churn),
            'pending': 0 if renewable else int(initial_users),
            'retain_rate': round(retain / total * 100, 1) if total > 0 else 0,
            'upgrade_rate': round(upgrade / total * 100, 1) if total > 0 else 0,
            'churn_rate': round(churn / total * 100, 1) if total > 0 else 0,
            'renewable': renewable
        })
    
    return pd.DataFrame(results)

def analyze_user_segments(df):
    """사용자 세그먼트 분석"""
    basic_users = df[df['product'] == 9]['idx'].unique()
    
    segments = {
        '첫결제': 0,
        '결제 이력 있음': 0,
        '기타': 0
    }
    
    for user_id in basic_users:
        user_payments = df[df['idx'] == user_id].sort_values('create')
        first_basic = user_payments[user_payments['product'] == 9].iloc[0]
        
        if first_basic['first'] == 1:
            segments['첫결제'] += 1
        else:
            premium_payments = user_payments[(user_payments['product'].isin([2, 6, 8])) & 
                                            (user_payments['create'] < first_basic['create'])]
            if len(premium_payments) > 0:
                segments['결제 이력 있음'] += 1
            else:
                segments['기타'] += 1
    
    return segments

def highlight_total_row(row):
    """총합 행 강조 스타일"""
    if row.iloc[0] == '총합':
        return ['background-color: #fffbeb; font-weight: bold'] * len(row)
    return [''] * len(row)

def render_payment_status(df):
    """탭 1: Basic 요금제 결제 현황 (전체 누적)"""
    
    st.markdown("### 📅 기간 설정")
    
    # 날짜 필터 (제한 없음)
    today = datetime.now().date()
    min_date_in_data = df[df['product'] == 9]['create'].min().date()
    max_date_in_data = df[df['product'] == 9]['create'].max().date()
    
    # 기본값: 2026년 2월 26일부터 최신 데이터까지
    from datetime import date
    default_start = date(2026, 2, 26)
    default_end = max_date_in_data
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "시작일",
            value=default_start,
            min_value=min_date_in_data,
            max_value=max_date_in_data,
            key="payment_start"
        )
    
    with col2:
        end_date = st.date_input(
            "종료일",
            value=default_end,
            min_value=min_date_in_data,
            max_value=max_date_in_data,
            key="payment_end"
        )
    
    # 날짜 필터링
    df_filtered = df[
        (df['create'].dt.date >= start_date) & 
        (df['create'].dt.date <= end_date)
    ].copy()
    
    # Basic 결제 데이터
    basic_payments = df_filtered[df_filtered['product'] == 9].copy()
    total_payments = len(basic_payments)
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); 
                    border-left: 4px solid #10b981; padding: 1.25rem; border-radius: 8px; margin: 1.5rem 0;'>
            <strong>📅 기간:</strong> {start_date.strftime('%Y년 %m월 %d일')} ~ {end_date.strftime('%Y년 %m월 %d일')}<br>
            <strong>💳 총 결제 건수:</strong> {total_payments:,}건 (재결제 포함)
        </div>
    """, unsafe_allow_html=True)
    
    # 섹션: Basic 요금제 결제 회원 성분 (결제 건수 기준)
    st.markdown("### 👥 Basic 요금제 결제 회원 성분")
    st.markdown("*결제자 성분을 분석한 결과입니다*")
    
    # 각 결제 건에 대해 성분 분석 및 국가별 집계
    segments = {'첫결제': 0, '결제 이력 있음': 0, '기타': 0}
    country_by_segment = {
        '첫결제': {},
        '결제 이력 있음': {},
        '기타': {}
    }
    
    for _, payment in basic_payments.iterrows():
        user_id = payment['idx']
        payment_date = payment['create']
        country = payment['country']
        
        # 해당 결제가 첫결제인지 확인
        if payment['first'] == 1:
            segment = '첫결제'
            segments[segment] += 1
        else:
            # 해당 결제 이전에 프리미엄 결제 이력이 있는지 확인
            user_payments = df[df['idx'] == user_id]
            prior_premium = user_payments[
                (user_payments['product'].isin([2, 6, 8])) & 
                (user_payments['create'] < payment_date)
            ]
            
            if len(prior_premium) > 0:
                segment = '결제 이력 있음'
                segments[segment] += 1
            else:
                segment = '기타'
                segments[segment] += 1
        
        # 국가별 집계
        country_by_segment[segment][country] = country_by_segment[segment].get(country, 0) + 1
    
    col1, col2 = st.columns(2)
    
    with col1:
        segment_df = pd.DataFrame(list(segments.items()), columns=['구분', '인원'])
        # 총합 행 추가
        total_row = pd.DataFrame([['총합', segment_df['인원'].sum()]], columns=['구분', '인원'])
        segment_display = pd.concat([segment_df, total_row], ignore_index=True)
        
        # 총합 행 스타일 적용
        styled_df = segment_display.style.apply(highlight_total_row, axis=1)
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
    
    with col2:
        fig = px.pie(
            segment_df,
            values='인원',
            names='구분',
            hole=0.4,
            color='구분',
            color_discrete_map={
                '첫결제': COLORS['retain'],
                '결제 이력 있음': COLORS['downgrade'],
                '기타': COLORS['pending']
            }
        )
        fig.update_traces(
            textposition='inside',
            textinfo='label+percent',
            textfont_size=12
        )
        fig.update_layout(
            height=400,
            showlegend=True,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 성분별 국가 분포
    st.markdown("### 🌍 성분별 국가 분포")
    
    tab1, tab2, tab3 = st.tabs(["첫결제", "결제 이력 있음", "기타"])
    
    for idx, (tab, segment) in enumerate([(tab1, '첫결제'), (tab2, '결제 이력 있음'), (tab3, '기타')]):
        with tab:
            country_data = country_by_segment[segment]
            if country_data:
                # 데이터프레임 생성
                country_list = []
                total_count = sum(country_data.values())
                
                for country_code, count in sorted(country_data.items(), key=lambda x: x[1], reverse=True):
                    country_list.append({
                        '국가명': get_country_name_kr(country_code),
                        '명수': count,
                        '퍼센트': f"{count/total_count*100:.1f}%",
                        '티어': get_tier(country_code)
                    })
                
                country_df = pd.DataFrame(country_list)
                st.dataframe(country_df, hide_index=True, use_container_width=True)
            else:
                st.info("해당 성분의 데이터가 없습니다.")

def render_cohort_analysis(df):
    """탭 2: 코호트 상세 분석"""
    
    st.markdown("### 📅 코호트 분석 기간 설정")
    
    # 선택 가능한 최대 결제일 = 오늘 - 31일 (만료일이 확실히 지난 것만)
    today = datetime.now().date()
    max_date = today - timedelta(days=31)
    
    # 데이터에서 가능한 최소/최대 날짜
    min_date_in_data = df[df['product'] == 9]['create'].min().date()
    
    # 기본값: 최근 30일간의 결제자 (만료일 기준)
    default_end = max_date
    default_start = max(min_date_in_data, max_date - timedelta(days=29))
    
    # 안내 메시지
    st.markdown(f"""
        <div style='background: #fef3c7; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.9rem;'>
            💡 <strong>만료일이 지난 결제만 선택 가능</strong><br>
            선택 가능 최대: {max_date.strftime('%Y-%m-%d')} (오늘 기준 31일 전 결제)
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "시작일",
            value=default_start,
            min_value=min_date_in_data,
            max_value=max_date,
            key="cohort_start"
        )
    
    with col2:
        end_date = st.date_input(
            "종료일",
            value=default_end,
            min_value=min_date_in_data,
            max_value=max_date,
            key="cohort_end"
        )
    
    # 날짜 범위 검증
    if start_date > end_date:
        st.error("⚠️ 시작일이 종료일보다 늦습니다.")
        return
    
    # 날짜 필터링된 데이터 (코호트 대상)
    df_filtered = df[
        (df['create'].dt.date >= start_date) & 
        (df['create'].dt.date <= end_date)
    ].copy()
    
    # 코호트 분석 (전체 df와 필터링된 df 모두 전달)
    cohort_results = analyze_cohorts(df, df_filtered)
    segments = analyze_user_segments(df_filtered)
    
    # 코호트 분석 대상 모수
    basic_payments = df_filtered[df_filtered['product'] == 9]
    unique_users = basic_payments['idx'].nunique()
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); 
                    border-left: 4px solid #3b82f6; padding: 1.25rem; border-radius: 8px; margin-bottom: 2rem;'>
            <h3 style='margin: 0 0 0.75rem 0; color: #1e40af;'>📊 코호트 분석 대상 모수</h3>
            <strong>📅 분석 기간:</strong> {start_date.strftime('%Y년 %m월 %d일')} ~ {end_date.strftime('%Y년 %m월 %d일')}<br>
            <strong>👥 초기 모수:</strong> {unique_users:,}명 (고유 사용자)<br>
            <div style='margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(59, 130, 246, 0.3);'>
                <strong>회원 성분:</strong><br>
                • 첫결제: {segments['첫결제']}명 ({segments['첫결제']/unique_users*100:.1f}%)<br>
                • 결제 이력 있음: {segments['결제 이력 있음']}명 ({segments['결제 이력 있음']/unique_users*100:.1f}%)<br>
                • 기타: {segments['기타']}명 ({segments['기타']/unique_users*100:.1f}%)
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 일별 잔존율 현황
    st.markdown("### 📊 일별 잔존율 현황")
    
    sort_order = st.radio("정렬", ["오래된순", "최신순"], horizontal=True, key="cohort_sort")
    
    sorted_cohorts = cohort_results.sort_values(
        'cohort_date', 
        ascending=(sort_order == "오래된순")
    )
    
    display_cohorts = sorted_cohorts.head(7) if len(sorted_cohorts) > 7 else sorted_cohorts
    
    # 총합 행 계산
    total_summary = {
        'cohort_date': '총합',
        'initial_users': sorted_cohorts['initial_users'].sum(),
        'retain': sorted_cohorts['retain'].sum(),
        'upgrade': sorted_cohorts['upgrade'].sum(),
        'churn': sorted_cohorts['churn'].sum(),
        'pending': sorted_cohorts['pending'].sum(),
        'retain_rate': '',
        'upgrade_rate': '',
        'churn_rate': ''
    }
    
    # 총합의 비율 계산 (만료된 것만)
    renewable_total = sorted_cohorts[sorted_cohorts['renewable'] == True]
    if len(renewable_total) > 0:
        total_retain = renewable_total['retain'].sum()
        total_upgrade = renewable_total['upgrade'].sum()
        total_churn = renewable_total['churn'].sum()
        total = total_retain + total_upgrade + total_churn
        if total > 0:
            total_summary['retain_rate'] = f"{round(total_retain / total * 100, 1)}%"
            total_summary['upgrade_rate'] = f"{round(total_upgrade / total * 100, 1)}%"
            total_summary['churn_rate'] = f"{round(total_churn / total * 100, 1)}%"
    
    # 율 컬럼에 % 추가
    display_cohorts_copy = display_cohorts.copy()
    display_cohorts_copy['retain_rate'] = display_cohorts_copy['retain_rate'].apply(lambda x: f"{x}%" if x != '' and x == x else '')
    display_cohorts_copy['upgrade_rate'] = display_cohorts_copy['upgrade_rate'].apply(lambda x: f"{x}%" if x != '' and x == x else '')
    display_cohorts_copy['churn_rate'] = display_cohorts_copy['churn_rate'].apply(lambda x: f"{x}%" if x != '' and x == x else '')
    
    # 총합 행 추가
    total_row_df = pd.DataFrame([total_summary])
    display_with_total = pd.concat([display_cohorts_copy, total_row_df], ignore_index=True)
    
    # 총합 행 스타일 적용
    styled_df = display_with_total[[
        'cohort_date', 'initial_users', 'retain', 'upgrade', 'churn',
        'retain_rate', 'upgrade_rate', 'churn_rate'
    ]].rename(columns={
        'cohort_date': '코호트 날짜',
        'initial_users': '초기 결제자',
        'retain': 'Basic 유지',
        'upgrade': '업그레이드',
        'churn': '이탈(잠재결제자)',
        'retain_rate': '유지율',
        'upgrade_rate': '업그레이드율',
        'churn_rate': '이탈율'
    }).style.apply(highlight_total_row, axis=1)
    
    st.dataframe(
        styled_df,
        hide_index=True,
        use_container_width=True
    )
    
    if len(sorted_cohorts) > 7:
        if st.button(f"더보기 ({len(sorted_cohorts) - 7}개 더 있음)", key="cohort_more"):
            # 전체 데이터에 % 추가
            all_cohorts_copy = sorted_cohorts.copy()
            all_cohorts_copy['retain_rate'] = all_cohorts_copy['retain_rate'].apply(lambda x: f"{x}%" if x != '' and x == x else '')
            all_cohorts_copy['upgrade_rate'] = all_cohorts_copy['upgrade_rate'].apply(lambda x: f"{x}%" if x != '' and x == x else '')
            all_cohorts_copy['churn_rate'] = all_cohorts_copy['churn_rate'].apply(lambda x: f"{x}%" if x != '' and x == x else '')
            
            # 전체 데이터에 총합 행 추가
            all_with_total = pd.concat([all_cohorts_copy, total_row_df], ignore_index=True)
            
            # 총합 행 스타일 적용
            styled_all = all_with_total[[
                'cohort_date', 'initial_users', 'retain', 'upgrade', 'churn',
                'retain_rate', 'upgrade_rate', 'churn_rate'
            ]].rename(columns={
                'cohort_date': '코호트 날짜',
                'initial_users': '초기 결제자',
                'retain': 'Basic 유지',
                'upgrade': '업그레이드',
                'churn': '이탈(잠재결제자)',
                'retain_rate': '유지율',
                'upgrade_rate': '업그레이드율',
                'churn_rate': '이탈율'
            }).style.apply(highlight_total_row, axis=1)
            
            st.dataframe(
                styled_all,
                hide_index=True,
                use_container_width=True
            )
    
    # 전환 흐름 요약
    st.markdown("### 🔄 전환 흐름 요약")
    
    renewable = cohort_results[cohort_results['renewable'] == True]
    total_retain = renewable['retain'].sum()
    total_upgrade = renewable['upgrade'].sum()
    total_churn = renewable['churn'].sum()
    total = total_retain + total_upgrade + total_churn
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🟢 Basic 유지", 
            f"{total_retain:,}명 ({total_retain/total*100:.1f}%)" if total > 0 else f"{total_retain:,}명 (0%)"
        )
    
    with col2:
        st.metric(
            "🟠 업그레이드 (Basic→Prem.)", 
            f"{total_upgrade:,}명 ({total_upgrade/total*100:.1f}%)" if total > 0 else f"{total_upgrade:,}명 (0%)"
        )
    
    with col3:
        st.metric(
            "🔴 이탈(잠재결제자)", 
            f"{total_churn:,}명 ({total_churn/total*100:.1f}%)" if total > 0 else f"{total_churn:,}명 (0%)"
        )
    
    # 도넛 차트
    flow_data = pd.DataFrame({
        '구분': ['Basic 유지', '업그레이드', '이탈(잠재결제자)'],
        '인원': [total_retain, total_upgrade, total_churn]
    })
    
    fig = px.pie(
        flow_data,
        values='인원',
        names='구분',
        hole=0.4,
        color='구분',
        color_discrete_map={
            'Basic 유지': COLORS['retain'],
            '업그레이드': COLORS['upgrade'],
            '이탈(잠재결제자)': COLORS['churn']
        }
    )
    fig.update_traces(
        textposition='inside',
        textinfo='label+percent',
        textfont_size=12
    )
    fig.update_layout(
        height=400,
        showlegend=True,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 티어별 분포
    st.markdown("### 🌍 티어별 분포")
    
    tab1, tab2, tab3 = st.tabs(["Basic 유지", "업그레이드 (Basic→Prem.)", "이탈(잠재결제자)"])
    
    # 티어별 분포 계산
    tier_dist = {
        'retain': {'1티어': 0, '2티어': 0, '3티어': 0, 'Others': 0},
        'upgrade': {'1티어': 0, '2티어': 0, '3티어': 0, 'Others': 0},
        'churn': {'1티어': 0, '2티어': 0, '3티어': 0, 'Others': 0}
    }
    
    country_dist = {
        'retain': {},
        'upgrade': {},
        'churn': {}
    }
    
    for _, cohort in renewable.iterrows():
        cohort_date = pd.to_datetime(cohort['cohort_date'])
        expiry_date = cohort_date + pd.Timedelta(days=30)
        
        # 해당 코호트 날짜에 Basic 결제한 사람들 (필터링된 데이터에서)
        cohort_members = df_filtered[(df_filtered['product'] == 9) & (df_filtered['create'].dt.date == cohort_date.date())]
        
        for _, member in cohort_members.iterrows():
            member_id = member['idx']
            tier = member['tier']
            country = member['country']
            
            # 재결제 여부는 전체 데이터에서 확인
            member_payments = df[df['idx'] == member_id].sort_values('create')
            after_expiry = member_payments[member_payments['create'] > expiry_date]
            
            if len(after_expiry) == 0:
                tier_dist['churn'][tier] += 1
                country_dist['churn'][country] = country_dist['churn'].get(country, 0) + 1
            else:
                first_renewal = after_expiry.iloc[0]
                if first_renewal['product'] == 9:
                    tier_dist['retain'][tier] += 1
                    country_dist['retain'][country] = country_dist['retain'].get(country, 0) + 1
                elif first_renewal['product'] in [2, 6, 8]:
                    tier_dist['upgrade'][tier] += 1
                    country_dist['upgrade'][country] = country_dist['upgrade'].get(country, 0) + 1
                else:
                    tier_dist['churn'][tier] += 1
                    country_dist['churn'][country] = country_dist['churn'].get(country, 0) + 1
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            tier_df = pd.DataFrame(list(tier_dist['retain'].items()), columns=['티어', '인원'])
            fig = px.pie(tier_df, values='인원', names='티어', hole=0.4)
            fig.update_traces(
                textposition='inside',
                textinfo='label+percent',
                textfont_size=12
            )
            fig.update_layout(
                height=400,
                showlegend=True,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 국가별 분포")
            if country_dist['retain']:
                country_list = []
                total_count = sum(country_dist['retain'].values())
                
                for country_code, count in sorted(country_dist['retain'].items(), key=lambda x: x[1], reverse=True):
                    country_list.append({
                        '국가명': get_country_name_kr(country_code),
                        '명수': count,
                        '퍼센트': f"{count/total_count*100:.1f}%",
                        '티어': get_tier(country_code)
                    })
                
                country_df = pd.DataFrame(country_list)
                st.dataframe(country_df, hide_index=True, use_container_width=True)
            else:
                st.info("데이터가 없습니다.")
    
    with tab2:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            tier_df = pd.DataFrame(list(tier_dist['upgrade'].items()), columns=['티어', '인원'])
            fig = px.pie(tier_df, values='인원', names='티어', hole=0.4)
            fig.update_traces(
                textposition='inside',
                textinfo='label+percent',
                textfont_size=12
            )
            fig.update_layout(
                height=400,
                showlegend=True,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 국가별 분포")
            if country_dist['upgrade']:
                country_list = []
                total_count = sum(country_dist['upgrade'].values())
                
                for country_code, count in sorted(country_dist['upgrade'].items(), key=lambda x: x[1], reverse=True):
                    country_list.append({
                        '국가명': get_country_name_kr(country_code),
                        '명수': count,
                        '퍼센트': f"{count/total_count*100:.1f}%",
                        '티어': get_tier(country_code)
                    })
                
                country_df = pd.DataFrame(country_list)
                st.dataframe(country_df, hide_index=True, use_container_width=True)
            else:
                st.info("데이터가 없습니다.")
    
    with tab3:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            tier_df = pd.DataFrame(list(tier_dist['churn'].items()), columns=['티어', '인원'])
            fig = px.pie(tier_df, values='인원', names='티어', hole=0.4)
            fig.update_traces(
                textposition='inside',
                textinfo='label+percent',
                textfont_size=12
            )
            fig.update_layout(
                height=400,
                showlegend=True,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 국가별 분포")
            if country_dist['churn']:
                country_list = []
                total_count = sum(country_dist['churn'].values())
                
                for country_code, count in sorted(country_dist['churn'].items(), key=lambda x: x[1], reverse=True):
                    country_list.append({
                        '국가명': get_country_name_kr(country_code),
                        '명수': count,
                        '퍼센트': f"{count/total_count*100:.1f}%",
                        '티어': get_tier(country_code)
                    })
                
                country_df = pd.DataFrame(country_list)
                st.dataframe(country_df, hide_index=True, use_container_width=True)
            else:
                st.info("데이터가 없습니다.")
    
    # 업그레이드 상품별 분포
    st.markdown("### 📈 업그레이드 상품별 분포")
    
    upgrade_products = {}
    
    for _, cohort in renewable.iterrows():
        cohort_date = pd.to_datetime(cohort['cohort_date'])
        expiry_date = cohort_date + pd.Timedelta(days=30)
        
        # 해당 코호트 날짜에 Basic 결제한 사람들 (필터링된 데이터에서)
        cohort_members = df_filtered[(df_filtered['product'] == 9) & (df_filtered['create'].dt.date == cohort_date.date())]['idx'].unique()
        
        for member_id in cohort_members:
            # 재결제 여부는 전체 데이터에서 확인
            member_payments = df[df['idx'] == member_id].sort_values('create')
            after_expiry = member_payments[member_payments['create'] > expiry_date]
            
            if len(after_expiry) > 0:
                first_renewal = after_expiry.iloc[0]
                if first_renewal['product'] in [2, 6, 8]:
                    product = first_renewal['product']
                    upgrade_products[product] = upgrade_products.get(product, 0) + 1
    
    PRODUCTS = {
        9: 'Basic',
        2: 'Premium',
        6: 'Premium One Pass',
        8: 'Premium in-app'
    }
    
    upgrade_df = pd.DataFrame([
        {'상품': PRODUCTS[k], '인원': v} for k, v in upgrade_products.items()
    ])
    
    fig = px.bar(upgrade_df, x='상품', y='인원', color_discrete_sequence=[COLORS['upgrade']])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def main():
    # 페이지 너비 제한
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1200px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 헤더
    st.markdown("""
        <div style='background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0;'>📊 Basic 요금제 분석</h1>
            <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;'>Basic 요금제 성분 분석 및 결제 추이 분석</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 데이터 로드
    with st.spinner('데이터 로딩 중...'):
        df = load_data()
    
    if df is None:
        st.stop()
    
    st.success(f"✅ 데이터 로드 완료: 총 {len(df):,}건의 결제 데이터")
    
    # 탭 구조
    tab1, tab2 = st.tabs(["📊 Basic 요금제 성분 분석", "🎯 코호트 상세 분석(결제 추이)"])
    
    # === 탭 1: Basic 요금제 결제 현황 ===
    with tab1:
        render_payment_status(df)
    
    # === 탭 2: 코호트 상세 분석 ===
    with tab2:
        render_cohort_analysis(df)

if __name__ == "__main__":
    main()