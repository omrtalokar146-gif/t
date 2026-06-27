import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ccxt
import os
from dotenv import load_dotenv

# Load local environment variables if available
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Crypto Trading Signal Generator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom responsive CSS injection
st.markdown("""
<style>
    /* Styling metrics card */
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #334155;
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 1.6rem;
        color: #f8fafc;
        font-weight: 700;
    }
    /* Signal badges */
    .badge {
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 1.1rem;
        display: inline-block;
    }
    .badge-buy {
        background-color: #10b981;
        color: white;
    }
    .badge-sell {
        background-color: #ef4444;
        color: white;
    }
    .badge-wait {
        background-color: #6b7280;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# App Title & Header
st.title("📈 Crypto Trading Signal Generator")
st.caption("Professional mobile-responsive trading signals featuring Confluence Strategy (EMA, RSI, Patterns)")

# Sidebar Settings
st.sidebar.header("⚙️ Configuration")

# Exchange selection (Binance by default)
exchange_name = "binance"

st.sidebar.subheader("🔑 API Credentials (Optional)")
st.sidebar.info("Leave black to use Binance public endpoints (read-only, no API key required).")
api_key = st.sidebar.text_input("Binance API Key", value=os.getenv("BINANCE_API_KEY", ""), type="password")
api_secret = st.sidebar.text_input("Binance API Secret", value=os.getenv("BINANCE_API_SECRET", ""), type="password")

st.sidebar.subheader("📊 Market Selection")
trading_pair = st.sidebar.text_input("Trading Pair (e.g. BTC/USDT)", "BTC/USDT").upper()
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)
limit = st.sidebar.slider("Historical Candles Limit", min_value=100, max_value=1000, value=300, step=50)

# Init exchange client
@st.cache_resource
def get_exchange_client(_api_key=None, _api_secret=None):
    params = {}
    if _api_key and _api_secret:
        params['apiKey'] = _api_key
        params['secret'] = _api_secret
    
    # Init rate-limited CCXT binance client
    return ccxt.binance({
        **params,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })

try:
    exchange = get_exchange_client(api_key if api_key else None, api_secret if api_secret else None)
except Exception as e:
    st.error(f"Failed to initialize exchange connection: {str(e)}")
    st.stop()

# Load Market Data
@st.cache_data(ttl=30)  # Cache for 30s for quick refreshes
def fetch_ohlcv(symbol, tf, candle_count):
    # Map pair to clean CCXT/Binance format
    formatted_symbol = symbol.replace("/", "").replace("-", "")
    # Check if pair is available on exchange
    try:
        # Fetch OHLCV bar values
        ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=candle_count)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        raise ValueError(f"Failed to load data for {symbol} ({tf}). Details: {str(e)}")

# Candlestick Pattern Logic (Pure Python/Pandas logic to bypass C-dependencies)
def detect_candlestick_patterns(df):
    patterns = []
    
    for i in range(len(df)):
        if i < 1:
            patterns.append("None")
            continue
            
        o_curr, h_curr, l_curr, c_curr = df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i]
        o_prev, h_prev, l_prev, c_prev = df['open'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1], df['close'].iloc[i-1]
        
        body_curr = abs(c_curr - o_curr)
        range_curr = h_curr - l_curr
        
        body_prev = abs(c_prev - o_prev)
        
        pattern_detected = "None"
        
        # 1. DOJI
        # Body is extremely small (<10%) compared to entire range
        if range_curr > 0 and body_curr / range_curr < 0.1:
            pattern_detected = "Doji"
            
        # 2. HAMMER (Bullish)
        # Small body at upper end, long lower wick (at least 2x body), little or no upper wick
        else:
            lower_wick = min(o_curr, c_curr) - l_curr
            upper_wick = h_curr - max(o_curr, c_curr)
            if body_curr > 0 and lower_wick >= (2 * body_curr) and upper_wick <= (0.5 * body_curr):
                pattern_detected = "Hammer (Bull)"
                
            # 3. ENGULFING
            # Bullish Engulfing
            elif c_prev < o_prev and c_curr > o_curr and c_curr > o_prev and o_curr < c_prev:
                pattern_detected = "Bullish Engulfing"
            # Bearish Engulfing
            elif c_prev > o_prev and c_curr < o_curr and c_curr < o_prev and o_curr > c_prev:
                pattern_detected = "Bearish Engulfing"
                
        patterns.append(pattern_detected)
        
    df['Pattern'] = patterns
    return df

# Start calculation and visual layout
if trading_pair:
    with st.spinner(f"Fetching market data for {trading_pair}..."):
        try:
            # Load real-time OHLCV
            df = fetch_ohlcv(trading_pair, timeframe, limit)
            
            # Apply Confluence Strategy indicators
            df['EMA_200'] = ta.ema(df['close'], length=200)
            df['RSI_14'] = ta.rsi(df['close'], length=14)
            df = detect_candlestick_patterns(df)
            
            # Extract latest values
            latest_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            current_price = latest_row['close']
            price_change = current_price - prev_row['close']
            pct_change = (price_change / prev_row['close']) * 100
            
            latest_rsi = latest_row['RSI_14']
            latest_ema = latest_row['EMA_200']
            latest_pattern = latest_row['Pattern']
            
            # Trend Evaluation
            if pd.isna(latest_ema):
                trend_status = "Insufficient candles (< 200) for EMA"
                trend_direction = "Neutral"
            else:
                trend_direction = "Bullish" if current_price > latest_ema else "Bearish"
                trend_status = f"{trend_direction} (Price above 200 EMA)" if trend_direction == "Bullish" else f"{trend_direction} (Price below 200 EMA)"

            # RSI Evaluation
            rsi_direction = "Neutral"
            if latest_rsi < 40:
                rsi_direction = "Oversold/Constructive"
            elif latest_rsi > 60:
                rsi_direction = "Overbought/Bearish"
            else:
                rsi_direction = "Sideways"

            # Confluence Signal Determination
            # STRICT RECONCILIATION:
            # - BUY: Price > EMA(200) AND RSI < 45 AND Pattern is Bullish Pattern (Bullish Engulfing, Hammer (Bull), Doji)
            # - SELL: Price < EMA(200) AND RSI > 55 AND Pattern is Bearish Pattern (Bearish Engulfing)
            # - OTHERWISE: WAIT
            
            signal = "WAIT"
            signal_color = "badge-wait"
            signal_reason = []

            if not pd.isna(latest_ema) and not pd.isna(latest_rsi):
                # Checking core elements
                is_bullish_trend = current_price > latest_ema
                is_bearish_trend = current_price < latest_ema
                is_rsi_buy = latest_rsi < 45
                is_rsi_sell = latest_rsi > 55
                is_pattern_bullish = latest_pattern in ["Bullish Engulfing", "Hammer (Bull)", "Doji"]
                is_pattern_bearish = latest_pattern in ["Bearish Engulfing", "Doji"]

                if is_bullish_trend and is_rsi_buy and is_pattern_bullish:
                    signal = "BUY"
                    signal_color = "badge-buy"
                    signal_reason = ["Price is is above 200 EMA (Bullish Trend)", "RSI is in a buy zone (< 45)", f"Bullish Pattern detected ({latest_pattern})"]
                elif is_bearish_trend and is_rsi_sell and is_pattern_bearish:
                    signal = "SELL"
                    signal_color = "badge-sell"
                    signal_reason = ["Price is below 200 EMA (Bearish Trend)", "RSI is in a sell zone (> 55)", f"Bearish Pattern detected ({latest_pattern})"]
                else:
                    if not is_bullish_trend and not is_bearish_trend:
                        signal_reason.append("Trend cannot be resolved.")
                    else:
                        signal_reason.append(f"Trend is {trend_direction}")
                    signal_reason.append(f"RSI is {latest_rsi:.1f} ({rsi_direction})")
                    signal_reason.append(f"Pattern detected: {latest_pattern}")
            else:
                signal_reason = ["Insufficient history. Please select a larger Candle count or wait for exchange data loading."]

            # Visual Display Section (Dashboard Grid)
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1.3])
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Price ({trading_pair})</div>
                    <div class="metric-value">${current_price:,.2f}</div>
                    <div style="font-size:0.85rem; color:{'#10b981' if price_change >= 0 else '#ef4444'}; font-weight:600;">
                        {'▲' if price_change >= 0 else '▼'} {price_change:,.2f} ({pct_change:+.2f}%)
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with col2:
                ema_display = f"${latest_ema:,.2f}" if not pd.isna(latest_ema) else "N/A"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">200 EMA (Trend)</div>
                    <div class="metric-value" style="font-size:1.4rem;">{ema_display}</div>
                    <div style="font-size:0.85rem; color:{'#10b981' if trend_direction == 'Bullish' else '#ef4444' if trend_direction == 'Bearish' else '#94a3b8'}; font-weight:600;">
                        Trend: {trend_direction}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with col3:
                rsi_display = f"{latest_rsi:.1f}" if not pd.isna(latest_rsi) else "N/A"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">RSI (14)</div>
                    <div class="metric-value">{rsi_display}</div>
                    <div style="font-size:0.85rem; color:#94a3b8; font-weight:600;">
                        Status: {rsi_direction}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with col4:
                reasons_html = "<br>".join([f"• {r}" for r in signal_reason])
                st.markdown(f"""
                <div class="metric-card" style="background-color: #0f172a; border-color: #475569;">
                    <div class="metric-title">Confluence Signal</div>
                    <div style="margin: 8px 0;">
                        <span class="badge {signal_color}">{signal}</span>
                    </div>
                    <div style="font-size:0.75rem; color:#94a3b8; line-height:1.2;">
                        {reasons_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Candlestick Pattern banner
            if latest_pattern != "None":
                st.success(f"🔥 Active Candlestick Pattern Triggered: **{latest_pattern}**")

            # Chart Block
            st.subheader("📊 Interactive Candlestick and Indicator Charts")
            
            # Setup Plotly Candle chart with EMA + RSI subplots
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.08, row_width=[0.3, 0.7])
            
            # Plot Klines
            fig.add_trace(go.Candlestick(
                x=df['datetime'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="Price Candles",
                increasing_line_color='#10b981',
                decreasing_line_color='#ef4444'
            ), row=1, col=1)
            
            # Plot 200 EMA
            if not pd.isna(latest_ema):
                fig.add_trace(go.Scatter(
                    x=df['datetime'],
                    y=df['EMA_200'],
                    name="200-period EMA",
                    line=dict(color='#f59e0b', width=2),
                ), row=1, col=1)
                
            # Plot RSI on subplot
            if not pd.isna(latest_rsi):
                fig.add_trace(go.Scatter(
                    x=df['datetime'],
                    y=df['RSI_14'],
                    name="RSI (14)",
                    line=dict(color='#6366f1', width=1.5),
                ), row=2, col=1)
                
                # Add RSI guidelines (30, 40, 60, 70)
                for level, color, style in [(30, 'red', 'dash'), (40, 'gray', 'dot'), (60, 'gray', 'dot'), (70, 'red', 'dash')]:
                    fig.add_line_marker_or_something_else_wait = None
                    fig.add_hline(y=level, line_width=1, line_dash=style, line_color=color, row=2, col=1)
                    
            # Layout customization
            fig.update_layout(
                height=550,
                margin=dict(l=20, r=20, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                xaxis=dict(gridcolor='#1e293b'),
                yaxis=dict(gridcolor='#1e293b', title="Price USD"),
                xaxis2=dict(gridcolor='#1e293b'),
                yaxis2=dict(gridcolor='#1e293b', title="RSI Level", range=[10, 90]),
                showlegend=True,
                legend=dict(x=0.01, y=0.99, bgcolor='rgba(15,23,42,0.8)'),
                xaxis_rangeslider_visible=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Interactive Candlestick analysis log
            with st.expander("📝 Detailed Candlestick Pattern Log (Latest 10 Candles)"):
                log_df = df[['datetime', 'open', 'high', 'low', 'close', 'Pattern']].tail(10).copy()
                log_df['datetime'] = log_df['datetime'].astype(str)
                st.dataframe(
                    log_df.rename(columns={'datetime': 'Timestamp', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'Pattern': 'Detected Pattern'}),
                    use_container_width=True,
                    hide_index=True
                )
                
        except Exception as e:
            st.error(f"❌ Error encountered: {str(e)}")
            st.warning("Ensure the trading pair symbol is supported on Binance (e.g., BTC/USDT, ETH/USDT, SOL/USDT) and standard spot rules apply.")

else:
    st.info("👈 Enter a valid trading pair in the sidebar (like BTC/USDT) to start real-time signal analysis.")
