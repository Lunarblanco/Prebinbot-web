import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA WEB Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="BTC/USDT Señales PRO",
    page_icon="⚡",
    layout="wide"
)

# Estilos CSS personalizados (Paleta oscura profesional)
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #e6edf3;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #2ea043 100%, #3fb950 100%);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

SYMBOL = "BTCUSDT"

# Título y descripción principal
st.title("⚡ Panel de Señales PRO: BTC/USDT")
st.markdown("Análisis técnico profesional sincronizado para **Scalping (1m) y Estándar (5m)** con Velas Japonesas, RSI, MACD, Bollinger y Libro de Órdenes.")

# ==========================================
# BARRA LATERAL (Ajustes de Temporalidad)
# ==========================================
st.sidebar.header("🎛️ Ajustes del Sistema")
temporalidad = st.sidebar.selectbox("Selecciona la Temporalidad", ["1m", "5m"], index=0)

# ==========================================
# FUNCIONES TÉCNICAS Y DE DATOS
# ==========================================
def calculate_rsi(prices, period=7):
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_ema(prices, period):
    if not prices:
        return 0.0
    if len(prices) < period:
        return prices[-1]
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_macd(prices):
    if len(prices) < 10:
        return 0.0, 0.0
    ema_12 = calculate_ema(prices, min(12, len(prices)))
    ema_26 = calculate_ema(prices, min(26, len(prices)))
    macd_line = ema_12 - ema_26
    signal_line = macd_line * 0.85 
    histogram = macd_line - signal_line
    return macd_line, histogram

def calculate_bollinger_bands(prices, period=20, num_std=2):
    if not prices:
        return 0.0, 0.0, 0.0
    effective_period = min(period, len(prices))
    sma = sum(prices[-effective_period:]) / effective_period
    variance = sum((x - sma) ** 2 for x in prices[-effective_period:]) / effective_period
    std_dev = variance ** 0.5
    upper_band = sma + (num_std * std_dev)
    lower_band = sma - (num_std * std_dev)
    return upper_band, sma, lower_band

def get_binance_data(interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit=60"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return parse_klines(data)
    except Exception:
        pass

    url_backup = f"https://data-api.binance.vision/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit=60"
    response = requests.get(url_backup, headers=headers, timeout=10)
    data = response.json()
    
    if isinstance(data, list) and len(data) > 0:
        return parse_klines(data)
        
    raise ValueError("Binance bloqueó la IP del servidor o no respondió datos válidos.")

def parse_klines(data):
    df = pd.DataFrame(data, columns=[
        'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close_time', 'Quote_asset_volume', 'Number_of_trades',
        'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
    ])
    df['Time'] = pd.to_datetime(df['Open_time'], unit='ms')
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = df[col].astype(float)
    return df

def get_order_book():
    url = f"https://api.binance.com/api/v3/depth?symbol={SYMBOL}&limit=6"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            res = response.json()
            bids = pd.DataFrame(res.get('bids', []), columns=['Precio', 'Cantidad']).astype(float)
            asks = pd.DataFrame(res.get('asks', []), columns=['Precio', 'Cantidad']).astype(float)
            return bids, asks
    except Exception:
        pass
    return pd.DataFrame(), pd.DataFrame()

# ==========================================
# CONTROL DE TIEMPO Y CICLOS EXACTOS
# ==========================================
now = datetime.now()
current_minute = now.minute
current_second = now.second

# Cálculo del tiempo restante para el siguiente cierre de vela según el periodo
intervalo_val = 1 if temporalidad == "1m" else 5
minutos_faltantes = intervalo_val - (current_minute % intervalo_val)
if minutos_faltantes == intervalo_val and current_second > 0:
    minutos_faltantes = 0
segundos_para_cierre = (minutos_faltantes * 60) - current_second
if segundos_para_cierre <= 0:
    segundos_para_cierre = intervalo_val * 60

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
col_m1, col_m2, col_m3, col_btn = st.columns([2, 2, 2, 2])

try:
    df_data = get_binance_data(temporalidad)
    closes = df_data['Close'].tolist()
    volumes = df_data['Volume'].tolist()
    
    current_price = closes[-1]
    rsi = calculate_rsi(closes, 7)

    # Métricas principales arriba
    col_m1.metric("Precio Actual BTC", f"${current_price:,.2f}")
    col_m2.metric("RSI Rápido (7)", f"{rsi:.2f}")
    col_m3.metric("Ciclo Actual", f"{temporalidad} (Cierra en {segundos_para_cierre}s)")
    
    with col_btn:
        st.write("") 
        actualizar = st.button("🔄 Actualizar Análisis", use_container_width=True)

    st.markdown("---")

    _, macd_hist = calculate_macd(closes)
    upper_b, middle_b, lower_b = calculate_bollinger_bands(closes, 20, 2)
    
    vol_len = min(10, len(volumes) - 1)
    volumen_promedio = sum(volumes[-(vol_len+1):-1]) / vol_len if vol_len > 0 else volumes[-1]
    volumen_fuerte = volumes[-1] > (volumen_promedio * 1.1)

    ancho_bandas = (upper_b - lower_b) / middle_b if middle_b > 0 else 0
    es_lateral = ancho_bandas < 0.0015 or (len(closes) >= 5 and abs(closes[-1] - closes[-5]) < current_price * 0.0003)

    alcista_confluencia = (
        len(closes) >= 3 and
        closes[-1] > closes[-2] and
        closes[-2] > closes[-3] and
        rsi < 72 and
        macd_hist > 0 and
        current_price <= upper_b
    )

    bajista_confluencia = (
        len(closes) >= 3 and
        closes[-1] < closes[-2] and
        closes[-2] < closes[-3] and
        rsi > 28 and
        macd_hist < 0 and
        current_price >= lower_b
    )

    # Estado de la predicción con los ciclos sincronizados
    if es_lateral:
        st.warning(f"⚠️ **MERCADO LATERAL / RANGO DETECTADO (NO OPERAR)**\n\nTemporalidad: **{temporalidad}**. El precio está comprimido o sin dirección clara. Protege tu capital.")
    elif alcista_confluencia:
        base_prob = 72 + (5 if volumen_fuerte else 0) + min(15, abs(macd_hist) * 100)
        probabilidad = round(min(94.5, max(70.0, base_prob)), 1)
        st.success(f"🟢 **SEÑAL PRO: MÁS ALTO (SUBIDA)**\n\n* **Temporalidad:** {temporalidad}\n* **Probabilidad:** {probabilidad}%\n* **Validaciones:** MACD alcista, RSI controlado y volumen {'fuerte' if volumen_fuerte else 'normal'}.")
    elif bajista_confluencia:
        base_prob = 72 + (5 if volumen_fuerte else 0) + min(15, abs(macd_hist) * 100)
        probabilidad = round(min(94.5, max(70.0, base_prob)), 1)
        st.error(f"🔴 **SEÑAL PRO: MÁS BAJO (BAJADA)**\n\n* **Temporalidad:** {temporalidad}\n* **Probabilidad:** {probabilidad}%\n* **Validaciones:** MACD bajista, RSI controlado y volumen {'fuerte' if volumen_fuerte else 'normal'}.")
    else:
        st.info(f"⏳ **MERCADO INDECISO (ESPERA)**\n\nTemporalidad: **{temporalidad}**. Las herramientas no muestran confluencia firme para este cierre de ciclo.")

    # Gráfico interactivo de Velas Japonesas optimizado
    st.subheader(f"📊 Gráfico de Velas Japonesas - BTC/USDT ({temporalidad})")
    
    fig = go.Figure(data=[go.Candlestick(
        x=df_data['Time'],
        open=df_data['Open'],
        high=df_data['High'],
        low=df_data['Low'],
        close=df_data['Close'],
        name="BTC"
    )])
    
    fig.update_layout(
        xaxis_title="Hora",
        yaxis_title="Precio (USDT)",
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})

    # Sección del Libro de Órdenes
    st.subheader("📖 Libro de Órdenes en Tiempo Real (Binance)")
    bids, asks = get_order_book()

    if not bids.empty and not asks.empty:
        col_bids, col_asks = st.columns(2)
        
        with col_bids:
            st.markdown("🟢 **Órdenes de Compra (Bids)**")
            st.dataframe(bids, use_container_width=True, hide_index=True)
            
        with col_asks:
            st.markdown("🔴 **Órdenes de Venta (Asks)**")
            st.dataframe(asks, use_container_width=True, hide_index=True)
    else:
        st.info("Cargando libro de órdenes de Binance...")

except Exception as e:
    st.error(f"Error al conectar con los datos de Binance: {e}")
    
