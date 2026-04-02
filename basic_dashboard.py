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

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1200px !important; /* 필요에 따라 1400px 등으로 조절하세요 */
    }
    </style>
    """,
    unsafe_allow_html=True
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

def analyze_cohorts(df):
    """코호트 분석 - HTML 버전과 동일한 로직"""
    today = pd.Timestamp.now().normalize()
    
    # Basic(product=9) 결제만 필터링
    basic_data = df[df['product'] == 9].copy()
    
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
                member_payments = df[df['idx'] == member_id].sort_values('create')
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
        '완전 신규': 0,
        '결제 이력 있음': 0,
        '기타': 0
    }
    
    for user_id in basic_users:
        user_payments = df[df['idx'] == user_id].sort_values('create')
        first_basic = user_payments[user_payments['product'] == 9].iloc[0]
        
        if first_basic['first'] == 1:
            segments['완전 신규'] += 1
        else:
            premium_payments = user_payments[(user_payments['product'].isin([2, 6, 8])) & 
                                            (user_payments['create'] < first_basic['create'])]
            if len(premium_payments) > 0:
                segments['결제 이력 있음'] += 1
            else:
                segments['기타'] += 1
    
    return segments

def main():
    # 헤더
    st.markdown("""
        <div style='background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0;'>📊 Basic 요금제 코호트 분석</h1>
            <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;'>Basic 요금제 사용자의 행동 패턴 분석</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 데이터 로드
    with st.spinner('데이터 로딩 중...'):
        df = load_data()
    
    if df is None:
        st.stop()
    
    st.success(f"✅ 데이터 로드 완료: 총 {len(df):,}건의 결제 데이터")
    
    # 코호트 분석
    cohort_results = analyze_cohorts(df)
    segments = analyze_user_segments(df)
    
    # 데이터 요약 정보
    basic_payments = df[df['product'] == 9]
    unique_users = basic_payments['idx'].nunique()
    latest_date = df['create'].max()
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); 
                    border-left: 4px solid #10b981; padding: 1.25rem; border-radius: 8px; margin-bottom: 2rem;'>
            <strong>📅 데이터 기준일:</strong> {latest_date.strftime('%Y년 %m월 %d일')}<br>
            <strong>👥 총 Basic 결제자:</strong> {unique_users:,}명 (재결제 포함 누적 {len(basic_payments):,}건)
        </div>
    """, unsafe_allow_html=True)
    
    # 섹션 5: Basic 요금제 결제 회원 성분
    st.markdown("### 👥 Basic 요금제 결제 회원 성분")
    
    col1, col2 = st.columns(2)
    
    with col1:
        segment_df = pd.DataFrame(list(segments.items()), columns=['구분', '인원'])
        st.dataframe(segment_df, hide_index=True, use_container_width=True)
    
    with col2:
        fig = px.pie(
            segment_df,
            values='인원',
            names='구분',
            hole=0.4,
            color='구분',
            color_discrete_map={
                '완전 신규': COLORS['retain'],
                '결제 이력 있음': COLORS['downgrade'],
                '기타': COLORS['pending']
            }
        )
        fig.update_layout(
            height=400,
            showlegend=True,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 섹션 1: 코호트별 잔존율 현황
    st.markdown("### 📊 섹션 1. 코호트별 잔존율 현황")
    
    sort_order = st.radio("정렬", ["오래된순", "최신순"], horizontal=True)
    
    sorted_cohorts = cohort_results.sort_values(
        'cohort_date', 
        ascending=(sort_order == "오래된순")
    )
    
    display_cohorts = sorted_cohorts.head(7) if len(sorted_cohorts) > 7 else sorted_cohorts
    
    st.dataframe(
        display_cohorts[[
            'cohort_date', 'initial_users', 'retain', 'upgrade', 'churn', 'pending',
            'retain_rate', 'upgrade_rate', 'churn_rate'
        ]].rename(columns={
            'cohort_date': '코호트 날짜',
            'initial_users': '초기 결제자',
            'retain': 'Basic 유지',
            'upgrade': '업그레이드',
            'churn': '이탈',
            'pending': '미만료',
            'retain_rate': '유지율',
            'upgrade_rate': '업그레이드율',
            'churn_rate': '이탈율'
        }),
        hide_index=True,
        use_container_width=True
    )
    
    if len(sorted_cohorts) > 7:
        if st.button(f"더보기 ({len(sorted_cohorts) - 7}개 더 있음)"):
            st.dataframe(
                sorted_cohorts[[
                    'cohort_date', 'initial_users', 'retain', 'upgrade', 'churn', 'pending',
                    'retain_rate', 'upgrade_rate', 'churn_rate'
                ]].rename(columns={
                    'cohort_date': '코호트 날짜',
                    'initial_users': '초기 결제자',
                    'retain': 'Basic 유지',
                    'upgrade': '업그레이드',
                    'churn': '이탈',
                    'pending': '미만료',
                    'retain_rate': '유지율',
                    'upgrade_rate': '업그레이드율',
                    'churn_rate': '이탈율'
                }),
                hide_index=True,
                use_container_width=True
            )
    
    # 섹션 2: 전환 흐름 요약
    st.markdown("### 🔄 섹션 2. 전환 흐름 요약")
    
    renewable = cohort_results[cohort_results['renewable'] == True]
    total_retain = renewable['retain'].sum()
    total_upgrade = renewable['upgrade'].sum()
    total_churn = renewable['churn'].sum()
    total = total_retain + total_upgrade + total_churn
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🟢 Basic 유지", f"{total_retain:,}명", 
                 f"{total_retain/total*100:.1f}%" if total > 0 else "0%")
    
    with col2:
        st.metric("🟠 업그레이드 (Basic→Prem.)", f"{total_upgrade:,}명",
                 f"{total_upgrade/total*100:.1f}%" if total > 0 else "0%")
    
    with col3:
        st.metric("🔴 이탈", f"{total_churn:,}명",
                 f"{total_churn/total*100:.1f}%" if total > 0 else "0%")
    
    # 도넛 차트
    flow_data = pd.DataFrame({
        '구분': ['Basic 유지', '업그레이드', '이탈'],
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
            '이탈': COLORS['churn']
        }
    )
    fig.update_layout(
        height=400,
        showlegend=True,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 섹션 3: 티어별 분포 (탭)
    st.markdown("### 🌍 섹션 3. 티어별 분포")
    
    tab1, tab2, tab3 = st.tabs(["Basic 유지", "업그레이드 (Basic→Prem.)", "이탈"])
    
    # 티어별 분포 계산 - HTML 버전과 동일
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
        
        # 해당 코호트 날짜에 Basic 결제한 사람들
        cohort_members = df[(df['product'] == 9) & (df['create'].dt.date == cohort_date.date())]
        
        for _, member in cohort_members.iterrows():
            member_id = member['idx']
            tier = member['tier']
            country = member['country']
            
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
        tier_df = pd.DataFrame(list(tier_dist['retain'].items()), columns=['티어', '인원'])
        fig = px.pie(tier_df, values='인원', names='티어', hole=0.4)
        fig.update_layout(
            height=400,
            showlegend=True,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        if st.button("상세보기 >", key="retain_detail"):
            country_df = pd.DataFrame(
                sorted(country_dist['retain'].items(), key=lambda x: x[1], reverse=True),
                columns=['국가', '명수']
            )
            country_df['퍼센트'] = (country_df['명수'] / country_df['명수'].sum() * 100).round(1)
            st.dataframe(country_df, hide_index=True, use_container_width=True)
    
    with tab2:
        tier_df = pd.DataFrame(list(tier_dist['upgrade'].items()), columns=['티어', '인원'])
        fig = px.pie(tier_df, values='인원', names='티어', hole=0.4)
        fig.update_layout(
            height=400,
            showlegend=True,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        if st.button("상세보기 >", key="upgrade_detail"):
            country_df = pd.DataFrame(
                sorted(country_dist['upgrade'].items(), key=lambda x: x[1], reverse=True),
                columns=['국가', '명수']
            )
            country_df['퍼센트'] = (country_df['명수'] / country_df['명수'].sum() * 100).round(1)
            st.dataframe(country_df, hide_index=True, use_container_width=True)
    
    with tab3:
        tier_df = pd.DataFrame(list(tier_dist['churn'].items()), columns=['티어', '인원'])
        fig = px.pie(tier_df, values='인원', names='티어', hole=0.4)
        fig.update_layout(
            height=400,
            showlegend=True,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        if st.button("상세보기 >", key="churn_detail"):
            country_df = pd.DataFrame(
                sorted(country_dist['churn'].items(), key=lambda x: x[1], reverse=True),
                columns=['국가', '명수']
            )
            country_df['퍼센트'] = (country_df['명수'] / country_df['명수'].sum() * 100).round(1)
            st.dataframe(country_df, hide_index=True, use_container_width=True)
    
    # 섹션 4: 업그레이드 상품별 분포
    st.markdown("### 📈 섹션 4. 업그레이드 상품별 분포")
    
    upgrade_products = {}
    
    for _, cohort in renewable.iterrows():
        cohort_date = pd.to_datetime(cohort['cohort_date'])
        expiry_date = cohort_date + pd.Timedelta(days=30)
        
        # 해당 코호트 날짜에 Basic 결제한 사람들
        cohort_members = df[(df['product'] == 9) & (df['create'].dt.date == cohort_date.date())]['idx'].unique()
        
        for member_id in cohort_members:
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

if __name__ == "__main__":
    main()