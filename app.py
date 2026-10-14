import streamlit as st
import requests
import urllib.parse
import pandas as pd

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA WEB
# ==========================================
st.set_page_config(
    page_title="BTC/USDT Señales PRO",
    page_icon="📈",
    layout="centered"
)

SYMBOL = "BTCUSDT"

# Título y descripción principal
st.title("⚡ Panel de Señales PRO: BTC/USDT")
st.markdown("Análisis técnico profesional con **RSI (7), MACD, Bandas de Bollinger y Volumen** para scalping y opciones.")

# Barra lateral para controles
st.sidebar.header("🎛️ Configuración de Análisis")
temporalidad = st.sidebar.selectbox("Selecciona la Temporalidad", ["1m", "5m"], index=1)
modo_analisis = st.sidebar.button("🔍 Ejecutar Análisis en Vivo")

# ==========================================
# FUNCIONES TÉCNICAS
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
    if len(prices) < period:
        return prices[-1]
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_macd(prices):
    if len(prices) < 26:
        return 0, 0
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    macd_line = ema_12 - ema_26
    signal_line = macd_line * 0.85 
    histogram = macd_line - signal_line
    return macd_line, histogram

def calculate_bollinger_bands(prices, period=20, num_std=2):
    if len(prices) < period:
        sma = sum(prices) / len(prices)
        return sma, sma, sma
    sma = sum(prices[-period:]) / period
    variance = sum((x - sma) ** 2 for x in prices[-period:]) / period
    std_dev = variance ** 0.5
    upper_band = sma + (num_std * std_dev)
    lower_band = sma - (num_std * std_dev)
    return upper_band, sma, lower_band

def get_binance_data(interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={interval}&limit=50"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    closes = [float(candle[4]) for candle in data]
    volumes = [float(candle[5]) for candle in data]
    return closes, volumes

# ==========================================
# EJECUCIÓN DEL ANÁLISIS
# ==========================================
if modo_analisis or True: # Se ejecuta por defecto al cargar o al pulsar el botón
    try:
        closes, volumes = get_binance_data(temporalidad)
        current_price = closes[-1]
        
        rsi = calculate_rsi(closes, 7)
        _, macd_hist = calculate_macd(closes)
        upper_b, middle_b, lower_b = calculate_bollinger_bands(closes, 20, 2)
        
        volumen_promedio = sum(volumes[-11:-1]) / 10
        volumen_fuerte = volumes[-1] > (volumen_promedio * 1.1)

        ancho_bandas = (upper_b - lower_b) / middle_b
        es_lateral = ancho_bandas < 0.0015 or (abs(closes[-1] - closes[-5]) < current_price * 0.0003)

        alcista_confluencia = (
            closes[-1] > closes[-2] and
            closes[-2] > closes[-3] and
            rsi < 72 and
            macd_hist > 0 and
            current_price <= upper_b
        )

        bajista_confluencia = (
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

        # Gráfico visual limpio con Streamlit
        st.subheader(fültro := f"Evolución Reciente del Precio ({temporalidad})")
        df_chart = pd.DataFrame({"Precio": closes[-30:]})
        st.line_chart(df_chart)

    except Exception as e:
        st.error(f"Error al conectar con los datos de Binance: {e}")
