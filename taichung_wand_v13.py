import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. 頁面基本設定
# ==========================================
st.set_page_config(page_title="估價作業-歐冠洋", layout="wide")
st.title("🎯 估價作業(比較法)-歐冠洋")

# ==========================================
# 2. 資料快取與載入函數
# ==========================================
@st.cache_data
def load_data(file):
    return pd.read_csv(file, engine='python', on_bad_lines='skip')

# ==========================================
# 3. 側邊欄：參數設定與過濾器
# ==========================================
st.sidebar.header("🔍 估價設定與空間過濾")

st.sidebar.subheader("🎯 目標標的座標設定")
target_address = st.sidebar.text_input("目標標的地址 (備忘標註用)", "臺中市西屯區文華路100號")
target_lat = st.sidebar.number_input("目標緯度 (Latitude)", value=24.17880, format="%.5f")
target_lon = st.sidebar.number_input("目標經度 (Longitude)", value=120.64630, format="%.5f")

st.sidebar.markdown("---")
radius_m = st.sidebar.slider("供需圈空間半徑 (公尺篩選)", 100, 2000, 500, 50)
months_range = st.sidebar.slider("交易時間範圍 (月)", 1, 36, 12)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 資料上傳區")
uploaded_realestate = st.sidebar.file_uploader("請上傳內政部實價登錄 CSV 檔", type=["csv"])

# ==========================================
# 4. 數據讀取與前處理
# ==========================================
df = None
if uploaded_realestate is not None:
    try:
        df = load_data(uploaded_realestate)
        st.sidebar.success(f"成功載入實價登錄！共 {len(df)} 筆。")
    except Exception as e:
        st.sidebar.error(f"讀取失敗: {e}")

# 內建模擬資料 (若未上傳)
if df is None:
    st.sidebar.info("💡 目前使用系統內建之示範資料進行展演。")
    df = pd.DataFrame({
        "鄉鎮市區": ["西屯區"] * 8,
        "土地區段位置或建物門牌": [
            "臺中市西屯區文華路10號", "臺中市西屯區文華路50號", "臺中市西屯區福星路100號", 
            "臺中市西屯區逢大路15號", "臺中市西屯區河南路二段200號", "臺中市西屯區青海路一段80號", 
            "臺中市西屯區福星北路20號(親友)", "臺中市西屯區西屯路三段300號(債權)"
        ],
        "交易年月日": [1141201, 1141015, 1140620, 1131201, 1140810, 1130315, 1141101, 1140901],
        "單價元平方公尺": [85000, 88000, 82000, 75000, 95000, 80000, 45000, 38000],
        "總價元": [8500000, 8900000, 8100000, 7200000, 12800000, 7900000, 4500000, 3800000],
        "建物型態": ["華廈", "華廈", "華廈", "公寓", "透天厝", "住宅大樓", "華廈", "公寓"],
        "建築完成年月": [10505, 10401, 10203, 8501, 11006, 9810, 10505, 8501],
        "備註": ["一般正常交易", "一般正常交易", "一般正常交易", "一般正常交易", 
               "一般正常交易", "一般正常交易", "親友間交易", "債權債務抵償"],
        "lat": [24.1795, 24.1775, 24.1810, 24.1750, 24.1700, 24.1650, 24.1830, 24.1600],
        "lon": [120.6455, 120.6470, 120.6430, 120.6480, 120.6550, 120.6600, 120.6420, 120.6500]
    })

# 座標與特徵補正
if 'lat' not in df.columns or 'lon' not in df.columns:
    np.random.seed(42)
    df['lat'] = target_lat + np.random.normal(0, 0.012, len(df))
    df['lon'] = target_lon + np.random.normal(0, 0.012, len(df))

if '單價元平方公尺' in df.columns and '單價_萬元_坪' not in df.columns:
    df['單價_元_坪'] = df['單價元平方公尺'] * 3.305785
    df['單價_萬元_坪'] = df['單價_元_坪'] / 10000

if '建築完成年月' in df.columns and '屋齡_年' not in df.columns:
    def calc_age(val):
        try:
            val_str = str(int(val)).zfill(5)
            return max(0, 2026 - (int(val_str[:-2]) + 1911))
        except:
            return 10
    df['屋齡_年'] = df['建築完成年月'].apply(calc_age)
elif '屋齡_年' not in df.columns:
    df['屋齡_年'] = 10

# ==========================================
# 5. 側邊欄：估價技術規則與調整係數設定
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("📐 不動產估價技術規則：調整率設定")
st.sidebar.markdown("依據比較法原則，設定各項專業調整係數（基準值為 1.00）")

adj_time_rate = st.sidebar.slider("1. 期日調整率 (每月市場漲跌 %)", -1.0, 2.0, 0.5, 0.1) / 100
adj_regional = st.sidebar.slider("2. 區域因素調整係數權重", 0.80, 1.20, 1.00, 0.01)
adj_individual = st.sidebar.slider("3. 個別因素調整係數權重", 0.80, 1.20, 1.00, 0.01)

st.sidebar.markdown("---")
st.sidebar.subheader("⚖️ 技術規則過濾")
exclude_abnormal = st.sidebar.checkbox("自動剔除異常/特殊交易", value=True)
if exclude_abnormal and '備註' in df.columns:
    pattern = '|'.join(['親友', '特殊', '債權', '抵償', '急買', '急賣', '拍賣'])
    df = df[~df['備註'].astype(str).str.contains(pattern, na=False)].copy()

if '建物型態' in df.columns:
    all_types = df['建物型態'].dropna().unique().tolist()
    selected_types = st.sidebar.multiselect("建物型態篩選", all_types, default=all_types)
    if selected_types:
        df = df[df['建物型態'].isin(selected_types)].copy()

if len(df) > 0 and '總價元' in df.columns:
    min_p, max_p = int(df['總價元'].min() / 10000), int(df['總價元'].max() / 10000)
    if min_p == max_p: max_p = min_p + 500
    price_slider = st.sidebar.slider("總價區間 (萬元)", min_p, max_p, (min_p, max_p))
    df = df[(df['總價元'] / 10000 >= price_slider[0]) & (df['總價元'] / 10000 <= price_slider[1])].copy()

# 空間距離計算 (Haversine formula)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2, dphi, dlambda = map(np.radians, [lat1, lat2, lat2 - lat1, lon2 - lon1])
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1-a)))

df['distance_m'] = calculate_distance(target_lat, target_lon, df['lat'], df['lon'])
df = df[df['distance_m'] <= radius_m].copy()

# ==========================================
# 6. 比較法專業試算邏輯
# ==========================================
if len(df) > 0:
    def calc_months_diff(val):
        try:
            val_str = str(int(val)).zfill(7)
            y = int(val_str[:3]) + 1911
            m = int(val_str[3:5])
            diff = (2026 - y) * 12 + (6 - m)
            return max(0, diff)
        except:
            return 6
            
    df['距今月數'] = df['交易年月日'].apply(calc_months_diff)
    df['期日調整係數'] = 1.0 + (df['距今月數'] * adj_time_rate)
    df['區域調整係數'] = adj_regional * (1.0 - (df['distance_m'] / 10000))
    df['個別調整係數'] = adj_individual * (1.0 + ((10 - df['屋齡_年']) / 100))
    
    df['比准單價_萬元_坪'] = df['單價_萬元_坪'] * df['期日調整係數'] * df['區域調整係數'] * df['個別調整係數']
    
    final_comparative_price = df['比准單價_萬元_坪'].mean()
    
    avg_building_ping = (df['總價元'].mean() / 10000) / df['單價_萬元_坪'].mean()
    final_comparative_total = final_comparative_price * avg_building_ping

# ==========================================
# 7. 主畫面：專業估價關鍵指標與 AI 總結
# ==========================================
if len(df) > 0:
    st.markdown("### 📊 不動產比較法：比准價格關鍵指標")
    col1, col2, col3 = st.columns(3)
    col1.metric("有效比較案例數", f"{len(df)} 筆")
    col2.metric("比較法試算比准單價", f"{final_comparative_price:.2f} 萬元/坪")
    col3.metric("比較法試算推估總價", f"{final_comparative_total:.0f} 萬元")
    
    st.info(f"💡 **估價技術總結**：以目標地址 **{target_address}** 為中心，半徑 **{radius_m} 公尺**供需圈內，經排除特殊交易並執行**期日、區域、個別因素調整**後，共篩選出 **{len(df)}** 筆有效比較案例。最終評定該標的之比准市價約落在 **{final_comparative_price:.1f} 萬元/坪**，推估總價約 **{final_comparative_total:.0f} 萬元**。")
else:
    st.warning("⚠ 在此條件下找不到符合的案例，請嘗試放寬左側拉桿或半徑！")

# ==========================================
# 8. 四大分頁展示
# ==========================================
if len(df) > 0:
    df_sorted = df.sort_values(by='比准單價_萬元_坪', ascending=False)

    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 空間供需圈地圖", "📋 比較法專業調整明細表", "📈 多維度價格分析", "💰 購屋財務與機會成本試算"])
    
    with tab1:
        st.subheader(f"供需圈空間檢視 (中心：{target_address} / 半徑：{radius_m} 公尺)")
        st.map(df[['lat', 'lon']], zoom=14)
        
    with tab2:
        st.subheader("不動產估價技術規則：比較法調整明細與試算表")
        st.markdown("下方表格完整記錄各比較標的的單價，並經過**期日調整係數、區域因素調整、個別因素調整**後，得出各案例之最終比准單價：")
        
        display_cols = [
            '土地區段位置或建物門牌', '交易年月日', '單價_萬元_坪', 
            '距今月數', '期日調整係數', '區域調整係數', '個別調整係數', '比准單價_萬元_坪', '備註'
        ]
        available_cols = [c for c in display_cols if c in df_sorted.columns]
        
        st.dataframe(df_sorted[available_cols], use_container_width=True)
        st.download_button(
            label="📥 下載完整比較法估價調整明細表 (CSV)",
            data=df_sorted.to_csv(index=False).encode('utf-8-sig'),
            file_name="valuation_comparison_method_ou.csv",
            mime="text/csv",
        )
        
    with tab3:
        st.subheader("區域市場多維度分析")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("**1. 歷史單價走勢 (時間 vs 價格)**")
            if '交易年月日' in df.columns:
                df_chart = df.sort_values(by='交易年月日').copy()
                df_chart['交易年月'] = df_chart['交易年月日'].astype(str).str[:-2]
                st.line_chart(data=df_chart, x='交易年月', y='單價_萬元_坪', height=350)
            else:
                st.info("無交易時間資料可繪製。")
                
        with col_chart2:
            st.markdown("**2. 屋齡與單價分佈 (屋齡 vs 價格)**")
            if '屋齡_年' in df.columns:
                st.scatter_chart(data=df, x='屋齡_年', y='單價_萬元_坪', height=350)
            else:
                st.info("無屋齡資料可繪製。")

    with tab4:
        st.subheader("實務應用：資金、現金流與資產配置機會成本評估")
        st.markdown("結合房地產估價與**價值型投資思維**：評估買房所需付出的頭期款，若轉為全職投入大盤 ETF（如 VOO / 0050），其長期複利機會成本為何。")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            total_price_wan = st.number_input("預估房屋總價 (萬元)", min_value=100, value=int(final_comparative_total), step=50)
        with c2:
            loan_percent = st.slider("預計貸款成數 (%)", 50, 90, 80, 5)
        with c3:
            interest_rate = st.number_input("房貸年利率 (%)", min_value=1.0, value=2.18, step=0.01)

        loan_years = st.radio("貸款年限", [20, 30, 40], index=1, horizontal=True)

        loan_amount = total_price_wan * 10000 * (loan_percent / 100)
        down_payment = total_price_wan * 10000 - loan_amount
        monthly_rate = (interest_rate / 100) / 12
        months = loan_years * 12
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1) if monthly_rate > 0 else loan_amount / months

        st.success(f"🛡️ **需準備自備款 (頭期款)：** 約 **{int(down_payment):,}** 元")
        st.error(f"🔥 **每月應繳本息：** 約 **{int(monthly_payment):,}** 元")
        
        st.markdown("---")
        st.subheader("⚖️ 價值型投資：資產配置機會成本與大盤 ETF 換算")
        
        col_etf_p1, col_etf_p2, col_etf_p3 = st.columns(3)
        with col_etf_p1:
            price_0050 = st.number_input("0050 當前預估市價 (元/股)", min_value=50.0, value=112.80, step=1.0)
        with col_etf_p2:
            price_voo_usd = st.number_input("VOO 當前預估市價 (美元/股)", min_value=100.0, value=707.54, step=5.0)
        with col_etf_p3:
            usd_twd = st.number_input("美元兌台幣匯率 (TWD/USD)", min_value=25.0, value=32.50, step=0.5)

        shares_0050_total = down_payment / price_0050
        lots_0050 = shares_0050_total / 1000
        voo_twd = price_voo_usd * usd_twd
        shares_voo = down_payment / voo_twd

        st.markdown(f"若把這筆 **{int(down_payment):,} 元** 的頭期款全數投入，相當於：")
        col_conv1, col_conv2 = st.columns(2)
        with col_conv1:
            st.info(f"🇹🇼 **可買進 0050**：約 **{lots_0050:.2f} 張** （共計約 {int(shares_0050_total):,} 股）")
        with col_conv2:
            st.info(f"🇺🇸 **可買進 VOO**：約 **{shares_voo:.1f} 股** （以匯率 {usd_twd:.2f} 元/股計算）")

        etf_cagr = st.slider("對比之大盤 ETF 預期年化報酬率 (%) (如 VOO / 0050)", 3.0, 15.0, 7.0, 0.5)
        years_horizon = 10  # 已改為 10 年
        
        fv_down_payment = down_payment * ((1 + (etf_cagr / 100)) ** years_horizon)
        opportunity_cost_gain = fv_down_payment - down_payment
        
        col_oc1, col_oc2 = st.columns(2)
        with col_oc1:
            st.metric("10 年後頭期款投入大盤複利總市值", f"約 {int(fv_down_payment):,} 元")
        with col_oc2:
            st.metric("10 年資本利得機會成本 (純益)", f"約 +{int(opportunity_cost_gain):,} 元", delta=f"{etf_cagr}% CAGR")
            
        st.info(f"💡 **理性觀點分析**：買房雖然滿足了居住剛需，但當您支付了 **{int(down_payment):,} 元** 的頭期款後（相當於把 **{lots_0050:.1f} 張 0050** 或 **{shares_voo:.1f} 股 VOO** 一次清空），這筆現金便失去了參與全球權益資產複利成長的機會。在預期年化報酬率 {etf_cagr}% 的假設下，10 年內您為了持有該房地產，隱含的機會成本高達 **{int(opportunity_cost_gain):,} 元** 的資本利得。這正是資產配置與現金流管理中必須權衡的代價。")