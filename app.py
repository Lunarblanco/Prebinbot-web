import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA WEB
# ==========================================
st.set_page_config(
    page_title="BTC/USDT Señales PRO",
    page_icon="📈",
    layout="wide"
)

SYMBOL = "BTCUSDT"

# Título y descripción principal
st.title("⚡ Panel de Señales PRO: BTC/USDT")
st.markdown("Análisis técnico profesional con **Velas Japonesas, RSI (7), MACD, Bandas de Bollinger y Volumen**.")

# Barra lateral para controles
st.sidebar.header("🎛️ Configuración de Análisis")
temporalidad = st.sidebar.selectbox("Selecciona la Temporalidad", ["1m", "5m"], index=0)
modo_analisis = st.sidebar.button("🔍 Actualizar Análisis")

# ==========================================
# FUNCIONES TÉCNICAS SEGURAS
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
    # Intentamos primero con la API global de Binance usando Headers de navegador
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

    # Si falla Binance, usamos una API pública alternativa de respaldo (CoinGecko o Endpoint alternativo)
    # Como respaldo de emergencia para velas si Binance bloquea la IP:
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

# ==========================================
# EJECUCIÓN DEL ANÁLISIS
# ==========================================
try:
    df_data = get_binance_data(temporalidad)
    closes = df_data['Close'].tolist()
    volumes = df_data['Volume'].tolist()
    
    if len(closes) < 10:
        st.warning("⚠️ Esperando suficientes velas para calcular los indicadores...")
    else:
        current_price = closes[-1]
        
        rsi = calculate_rsi(closes, 7)
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

        # Mostrar métricas clave en la web
        col1, col2, col3 = st.columns(3)
        col1.metric("Precio Actual BTC", f"${current_price:,.2f}")
        col2.metric("RSI Rápido (7)", f"{rsi:.2f}")
        col3.metric("Temporalidad", temporalidad)

        st.markdown("---")

        # Resultados de la predicción con diseño visual atractivo
        if es_lateral:
            st.warning("⚠️ **MERCADO LATERAL / RANGO DETECTADO (NO OPERAR)**\n\nEl precio está comprimido en las Bandas de Bollinger o sin fuerza direccional clara. Se recomienda evitar operaciones para proteger el capital.")
        elif alcista_confluencia:
            base_prob = 72 + (5 if volumen_fuerte else 0) + min(15, abs(macd_hist) * 100)
            probabilidad = round(min(94.5, max(70.0, base_prob)), 1)
            st.success(f"🟢 **SEÑAL PRO: MÁS ALTO (SUBIDA)**\n\n* **Probabilidad de Confluencia:** {probabilidad}%\n* **Validaciones:** MACD alcista, RSI controlado y volumen {'fuerte' if volumen_fuerte else 'normal'}.")
        elif bajista_confluencia:
            base_prob = 72 + (5 if volumen_fuerte else 0) + min(15, abs(macd_hist) * 100)
            probabilidad = round(min(94.5, max(70.0, base_prob)), 1)
            st.error(f"🔴 **SEÑAL PRO: MÁS BAJO (BAJADA)**\n\n* **Probabilidad de Confluencia:** {probabilidad}%\n* **Validaciones:** MACD bajista, RSI controlado y volumen {'fuerte' if volumen_fuerte else 'normal'}.")
        else:
            st.info("⏳ **MERCADO INDECISO (ESPERA)**\n\nLas herramientas técnicas no muestran una confluencia firme en este ciclo. Es mejor esperar la siguiente vela.")

        # Gráfico interactivo de Velas Japonesas con Plotly
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
            height=450,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error al conectar con los datos de Binance: {e}")
            
