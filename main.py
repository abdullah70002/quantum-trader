"""
╔══════════════════════════════════════════════════════╗
║       QUANTUM TRADER - Flet Android Application      ║
║       Mobile-First | Python Indicators Engine        ║
║       v1.0.0 — Refactored from Streamlit             ║
╚══════════════════════════════════════════════════════╝

How it works:
  • Flet handles all native Android UI widgets
  • A background thread runs a tiny HTTP server (stdlib only)
  • The server serves the lightweight-charts HTML page
  • ft.WebView loads that local URL — zero extra dependencies
  • IndicatorEngine logic is 100% identical to the original
"""

import flet as ft
import pandas as pd
import numpy as np
import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

# ──────────────────────────────────────────────
#  OPTIONAL IMPORTS  (graceful fallback)
# ──────────────────────────────────────────────
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# ──────────────────────────────────────────────
#  SETTINGS MANAGER
# ──────────────────────────────────────────────
SETTINGS_FILE = "quantum_trader_settings.json"

DEFAULT_SETTINGS = {
    "timeframe": "1h",
    "symbol": "BTC/USDT",
    "active_indicators": ["EMA_20", "EMA_50"],
    "theme": "dark",
    "last_updated": "",
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                return {**DEFAULT_SETTINGS, **saved}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    settings["last_updated"] = datetime.now().isoformat()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ──────────────────────────────────────────────
#  DATA ENGINE
# ──────────────────────────────────────────────
TIMEFRAME_MAP = {
    "1m":  {"ccxt": "1m",  "minutes": 1,    "yf": "1m",  "period": "1d"},
    "5m":  {"ccxt": "5m",  "minutes": 5,    "yf": "5m",  "period": "5d"},
    "15m": {"ccxt": "15m", "minutes": 15,   "yf": "15m", "period": "5d"},
    "1h":  {"ccxt": "1h",  "minutes": 60,   "yf": "1h",  "period": "30d"},
    "4h":  {"ccxt": "4h",  "minutes": 240,  "yf": "1h",  "period": "60d"},
    "1d":  {"ccxt": "1d",  "minutes": 1440, "yf": "1d",  "period": "500d"},
}


def fetch_ohlcv_ccxt(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    """Fetch OHLCV data from Binance via CCXT."""
    try:
        exchange = ccxt.binance({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        tf = TIMEFRAME_MAP.get(timeframe, {}).get("ccxt", "1h")
        ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df["time"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return df.dropna()
    except Exception:
        return pd.DataFrame()


def fetch_ohlcv_yfinance(symbol: str, timeframe: str) -> pd.DataFrame:
    """Fetch OHLCV data from Yahoo Finance as fallback."""
    try:
        yf_symbol = symbol.replace("/", "-")
        tf_info = TIMEFRAME_MAP.get(timeframe, TIMEFRAME_MAP["1h"])
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=tf_info["period"], interval=tf_info["yf"])
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        if "datetime" in df.columns:
            df["timestamp"] = pd.to_datetime(df["datetime"], utc=True)
        elif "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"], utc=True)
        df["time"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df = df.rename(columns={"stock splits": "splits", "dividends": "divs"})
        return df[["time", "open", "high", "low", "close", "volume"]].dropna().tail(500)
    except Exception:
        return pd.DataFrame()


def generate_demo_data(timeframe: str = "1h", n: int = 500) -> pd.DataFrame:
    """Realistic demo data when no internet connection is available."""
    np.random.seed(42)
    freq_map = {"1m": "min", "5m": "5min", "15m": "15min", "1h": "h", "4h": "4h", "1d": "D"}
    freq = freq_map.get(timeframe, "h")
    times = pd.date_range(end=datetime.now(tz=timezone.utc), periods=n, freq=freq)
    price = 45000.0
    prices, highs, lows, opens, volumes = [], [], [], [], []
    for _ in range(n):
        change  = np.random.normal(0, 0.008) * price
        open_p  = price
        close_p = price + change
        high_p  = max(open_p, close_p) * (1 + abs(np.random.normal(0, 0.003)))
        low_p   = min(open_p, close_p) * (1 - abs(np.random.normal(0, 0.003)))
        vol     = np.random.uniform(500, 3000)
        opens.append(open_p)
        prices.append(close_p)
        highs.append(high_p)
        lows.append(low_p)
        volumes.append(vol)
        price = close_p
    return pd.DataFrame({
        "time":   [t.strftime("%Y-%m-%d %H:%M:%S") for t in times],
        "open":   opens,
        "high":   highs,
        "low":    lows,
        "close":  prices,
        "volume": volumes,
    })


def fetch_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """Fetch with automatic fallback: CCXT → yFinance → Demo."""
    df = pd.DataFrame()
    if CCXT_AVAILABLE:
        df = fetch_ohlcv_ccxt(symbol, timeframe)
    if df.empty and YFINANCE_AVAILABLE:
        df = fetch_ohlcv_yfinance(symbol, timeframe)
    if df.empty:
        df = generate_demo_data(timeframe)
    return df


# ══════════════════════════════════════════════
#  INDICATOR ENGINE  — identical to original app.py
# ══════════════════════════════════════════════
class IndicatorEngine:
    """
    Indicator calculation engine.
    Add new indicators as @staticmethod methods.
    Each method receives a DataFrame and returns a pd.Series.
    """

    @staticmethod
    def EMA(df: pd.DataFrame, period: int = 20, source: str = "close") -> pd.Series:
        return df[source].ewm(span=period, adjust=False).mean()

    @staticmethod
    def SMA(df: pd.DataFrame, period: int = 20, source: str = "close") -> pd.Series:
        return df[source].rolling(window=period).mean()

    @staticmethod
    def RSI(df: pd.DataFrame, period: int = 14, source: str = "close") -> pd.Series:
        delta    = df[source].diff()
        gain     = delta.clip(lower=0)
        loss     = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs       = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def BOLLINGER_UPPER(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        sma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()
        return sma + (std * std_dev)

    @staticmethod
    def BOLLINGER_LOWER(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        sma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()
        return sma - (std * std_dev)

    @staticmethod
    def VWAP(df: pd.DataFrame, **kwargs) -> pd.Series:
        tp   = (df["high"] + df["low"] + df["close"]) / 3
        vwap = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
        return vwap

    @staticmethod
    def MACD_LINE(df: pd.DataFrame, fast: int = 12, slow: int = 26, **kwargs) -> pd.Series:
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        return ema_fast - ema_slow

    # ── Template: add your indicator here ──────
    # @staticmethod
    # def MY_INDICATOR(df: pd.DataFrame, period: int = 14) -> pd.Series:
    #     result = df["close"].rolling(window=period).apply(lambda x: YOUR_FORMULA(x))
    #     return result


INDICATOR_CONFIG: dict = {
    "EMA_20":  {"func": "EMA",             "params": {"period": 20},  "color": "#3b82f6", "name": "EMA 20"},
    "EMA_50":  {"func": "EMA",             "params": {"period": 50},  "color": "#f59e0b", "name": "EMA 50"},
    "EMA_200": {"func": "EMA",             "params": {"period": 200}, "color": "#ef4444", "name": "EMA 200"},
    "SMA_20":  {"func": "SMA",             "params": {"period": 20},  "color": "#10b981", "name": "SMA 20"},
    "BB_UP":   {"func": "BOLLINGER_UPPER", "params": {"period": 20},  "color": "#8b5cf6", "name": "BB Upper"},
    "BB_LOW":  {"func": "BOLLINGER_LOWER", "params": {"period": 20},  "color": "#8b5cf6", "name": "BB Lower"},
    "VWAP":    {"func": "VWAP",            "params": {},              "color": "#06b6d4", "name": "VWAP"},
}


def calculate_indicators(df: pd.DataFrame, active: list) -> dict:
    engine  = IndicatorEngine()
    results = {}
    for ind_id in active:
        if ind_id not in INDICATOR_CONFIG:
            continue
        cfg  = INDICATOR_CONFIG[ind_id]
        func = getattr(engine, cfg["func"], None)
        if func:
            try:
                values = func(df, **cfg["params"])
                results[ind_id] = {
                    "values": values,
                    "color":  cfg["color"],
                    "name":   cfg["name"],
                }
            except Exception:
                pass
    return results


# ──────────────────────────────────────────────
#  CHART HTML BUILDER  (lightweight-charts CDN)
# ──────────────────────────────────────────────
def build_chart_html(df: pd.DataFrame, indicators: dict, symbol: str = "BTC/USDT") -> str:
    """
    Generates a self-contained HTML page with a TradingView-style chart.
    Rendered inside ft.WebView via a local HTTP server.
    """
    candles_json = df[["time", "open", "high", "low", "close"]].to_json(orient="records")
    volume_json  = df[["time", "volume"]].rename(columns={"volume": "value"}).to_json(orient="records")

    lines_js = ""
    for ind_id, ind_data in indicators.items():
        vals      = ind_data["values"].dropna()
        line_data = []
        for idx, val in vals.items():
            if idx < len(df):
                line_data.append({"time": df.iloc[idx]["time"], "value": round(float(val), 4)})
        if not line_data:
            continue
        safe_id  = ind_id.replace("-", "_")
        line_json = json.dumps(line_data)
        color     = ind_data["color"]
        name      = ind_data["name"]
        lines_js += f"""
        var line_{safe_id} = chart.addLineSeries({{
            color: '{color}', lineWidth: 1.5,
            title: '{name}', priceLineVisible: false, lastValueVisible: true,
        }});
        line_{safe_id}.setData({line_json});
        """

    return f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0d1117; overflow:hidden; touch-action:none; }}
#chart {{ width:100vw; height:100vh; }}
#legend {{
  position:absolute; top:8px; left:8px; z-index:100;
  background:rgba(13,17,23,0.88); border:1px solid #30363d;
  border-radius:6px; padding:6px 10px;
  font-family:monospace; font-size:11px; color:#e6edf3;
  backdrop-filter:blur(4px); pointer-events:none;
}}
</style>
</head>
<body>
<div id="chart"></div>
<div id="legend">{symbol}</div>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
(function() {{
  var chart = LightweightCharts.createChart(document.getElementById('chart'), {{
    width:  window.innerWidth,
    height: window.innerHeight,
    layout: {{
      background: {{ type:'solid', color:'#0d1117' }},
      textColor:  '#8b949e', fontSize: 11,
    }},
    grid: {{
      vertLines: {{ color:'#161b22', style:1 }},
      horzLines: {{ color:'#161b22', style:1 }},
    }},
    crosshair: {{
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {{ color:'#3b82f6', labelBackgroundColor:'#1d4ed8' }},
      horzLine: {{ color:'#3b82f6', labelBackgroundColor:'#1d4ed8' }},
    }},
    rightPriceScale: {{ borderColor:'#21262d', textColor:'#8b949e' }},
    timeScale: {{ borderColor:'#21262d', textColor:'#8b949e', timeVisible:true, secondsVisible:false }},
    handleScroll: {{ mouseWheel:true, pressedMouseMove:true, horzTouchDrag:true, vertTouchDrag:false }},
    handleScale:  {{ axisPressedMouseMove:true, mouseWheel:true, pinch:true }},
  }});

  // ── Candlesticks ───────────────────────────
  var candleSeries = chart.addCandlestickSeries({{
    upColor:'#26a641', downColor:'#f85149',
    borderUpColor:'#26a641', borderDownColor:'#f85149',
    wickUpColor:'#26a641', wickDownColor:'#f85149',
  }});
  var candleData = {candles_json};
  candleSeries.setData(candleData);

  // ── Volume ─────────────────────────────────
  var volumeSeries = chart.addHistogramSeries({{
    color:'#3b82f6',
    priceFormat: {{ type:'volume' }},
    priceScaleId:'volume',
    scaleMargins: {{ top:0.85, bottom:0 }},
  }});
  var rawVol = {volume_json};
  volumeSeries.setData(rawVol.map(function(d, i) {{
    return {{
      time:  d.time,
      value: d.value,
      color: (i > 0 && candleData[i].close >= candleData[i].open)
               ? 'rgba(38,166,65,0.4)' : 'rgba(248,81,73,0.4)',
    }};
  }}));

  // ── Indicator lines ────────────────────────
  {lines_js}

  // ── Interactive legend ──────────────────────
  chart.subscribeCrosshairMove(function(param) {{
    if (!param.time || !param.seriesData) return;
    var ohlc = param.seriesData.get(candleSeries);
    if (!ohlc) return;
    var up  = ohlc.close >= ohlc.open;
    var col = up ? '#26a641' : '#f85149';
    document.getElementById('legend').innerHTML =
      '<b>{symbol}</b> ' +
      '<span style="color:#8b949e">O </span><span style="color:'+col+'">'+ ohlc.open.toFixed(2) +'</span> ' +
      '<span style="color:#8b949e">H </span><span style="color:#26a641">'+ ohlc.high.toFixed(2) +'</span> ' +
      '<span style="color:#8b949e">L </span><span style="color:#f85149">'+ ohlc.low.toFixed(2)  +'</span> ' +
      '<span style="color:#8b949e">C </span><span style="color:'+col+'">'+(up?'▲':'▼')+' '+ ohlc.close.toFixed(2) +'</span>';
  }});

  window.addEventListener('resize', function() {{
    chart.resize(window.innerWidth, window.innerHeight);
  }});

  chart.timeScale().fitContent();
}})();
</script>
</body>
</html>"""


# ──────────────────────────────────────────────
#  LOCAL HTTP SERVER  (stdlib — no extra deps)
#  Serves the chart HTML to ft.WebView
# ──────────────────────────────────────────────
_chart_store = {"html": "<html><body style='background:#0d1117'></body></html>"}
_SERVER_PORT  = 8765
_server_ready = threading.Event()


class _ChartHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = _chart_store["html"].encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type",   "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control",  "no-cache, no-store, must-revalidate")
        self.send_header("Pragma",         "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass   # silence server logs


def _run_server():
    try:
        srv = HTTPServer(("127.0.0.1", _SERVER_PORT), _ChartHandler)
        _server_ready.set()
        srv.serve_forever()
    except Exception as exc:
        print(f"[ChartServer] error: {exc}")


# Start once at module load
threading.Thread(target=_run_server, daemon=True, name="chart-server").start()
_server_ready.wait(timeout=3)


# ──────────────────────────────────────────────
#  FLET APPLICATION
# ──────────────────────────────────────────────
def main(page: ft.Page):
    # ── Page setup ──────────────────────────
    page.title        = "Quantum Trader"
    page.theme_mode   = ft.ThemeMode.DARK
    page.bgcolor      = "#0d1117"
    page.padding      = 0
    page.spacing      = 0
    page.window_width  = 400
    page.window_height = 850

    settings   = load_settings()
    _state     = {"df": pd.DataFrame(), "busy": False}

    # ── Live-update controls ────────────────
    price_text   = ft.Text("$--",    size=26, weight=ft.FontWeight.W_700, color="#e6edf3")
    change_text  = ft.Text("-- --",  size=13, color="#26a641")
    symbol_label = ft.Text(settings["symbol"], size=10, color="#8b949e")

    stat_h = ft.Text("H: --",        size=11, color="#8b949e")
    stat_l = ft.Text("L: --",        size=11, color="#8b949e")
    stat_v = ft.Text("Vol: --",      size=11, color="#8b949e")
    stat_t = ft.Text(f"TF: {settings['timeframe']}", size=11, color="#8b949e")
    stat_c = ft.Text("Candles: --",  size=11, color="#8b949e")

    rsi_val_text  = ft.Text("RSI: --", size=12, color="#3b82f6", weight=ft.FontWeight.W_600)
    rsi_lbl_text  = ft.Text("محايد",   size=11, color="#8b949e")
    ema20_text    = ft.Text("EMA20: --",size=12, color="#8b949e")

    time_text = ft.Text("",           size=10, color="#8b949e")
    src_text  = ft.Text("📡 --",      size=10, color="#8b949e")

    loading_ring = ft.ProgressRing(
        width=14, height=14,
        stroke_width=2,
        color="#3b82f6",
        visible=False,
    )

    # ── WebView (chart) ─────────────────────
    webview = ft.WebView(
        url=f"http://127.0.0.1:{_SERVER_PORT}",
        expand=True,
        javascript_enabled=True,
        on_page_started=lambda _: None,
        on_page_ended=lambda _: None,
    )
    chart_box = ft.Container(
        content=webview,
        height=420,
        bgcolor="#0d1117",
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    def _reload_webview():
        """Force the WebView to re-fetch the latest chart HTML."""
        webview.url = f"http://127.0.0.1:{_SERVER_PORT}?ts={int(time.time() * 1000)}"
        page.update()

    # ── Data load + render ──────────────────
    def _do_load_render():
        if _state["busy"]:
            return
        _state["busy"] = True
        loading_ring.visible = True
        try:
            page.update()
        except Exception:
            pass

        try:
            df = fetch_data(settings["symbol"], settings["timeframe"])
            _state["df"] = df
            if df.empty:
                return

            # Build + push chart HTML
            inds = calculate_indicators(df, settings["active_indicators"])
            _chart_store["html"] = build_chart_html(df, inds, settings["symbol"])
            _reload_webview()

            # Price stats
            last  = df["close"].iloc[-1]
            prev  = df["close"].iloc[-2] if len(df) > 1 else last
            chg   = last - prev
            chg_p = (chg / prev) * 100 if prev else 0
            h24   = df["high"].tail(24).max()
            l24   = df["low"].tail(24).min()
            v24   = df["volume"].tail(24).sum()

            price_text.value  = f"${last:,.2f}"
            symbol_label.value = settings["symbol"]
            if chg >= 0:
                change_text.value = f"▲ {abs(chg):,.2f}  ({abs(chg_p):.2f}%)"
                change_text.color = "#26a641"
            else:
                change_text.value = f"▼ {abs(chg):,.2f}  ({abs(chg_p):.2f}%)"
                change_text.color = "#f85149"

            stat_h.value = f"H: {h24:,.0f}"
            stat_l.value = f"L: {l24:,.0f}"
            stat_v.value = f"Vol: {v24:,.0f}"
            stat_t.value = f"TF: {settings['timeframe']}"
            stat_c.value = f"Candles: {len(df)}"

            # RSI
            engine  = IndicatorEngine()
            rsi_ser = engine.RSI(df)
            rv      = rsi_ser.iloc[-1]
            if rv > 70:
                rsi_val_text.color = "#ef4444"
                rsi_lbl_text.value = "ذروة شراء 🔴"
            elif rv < 30:
                rsi_val_text.color = "#26a641"
                rsi_lbl_text.value = "ذروة بيع 🟢"
            else:
                rsi_val_text.color = "#3b82f6"
                rsi_lbl_text.value = "محايد"
            rsi_val_text.value  = f"RSI: {rv:.1f}"
            ema20_text.value    = f"EMA20: {df['close'].ewm(span=20).mean().iloc[-1]:,.0f}"

            # Status bar
            dsrc         = "CCXT/Binance" if CCXT_AVAILABLE else ("yFinance" if YFINANCE_AVAILABLE else "Demo")
            src_text.value  = f"📡 {dsrc}"
            time_text.value = f"🕐 {datetime.now().strftime('%H:%M:%S')}"

            page.update()

        except Exception as exc:
            print(f"[load_render] {exc}")
        finally:
            _state["busy"] = False
            loading_ring.visible = False
            try:
                page.update()
            except Exception:
                pass

    def load_render():
        threading.Thread(target=_do_load_render, daemon=True).start()

    # ── Timeframe buttons ───────────────────
    TFS = ["1m", "5m", "15m", "1h", "4h", "1d"]

    def _tf_style(is_active: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            bgcolor={"": "#1d4ed8" if is_active else "#21262d"},
            color={"":  "#ffffff"  if is_active else "#8b949e"},
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            shape=ft.RoundedRectangleBorder(radius=6),
            side={"": ft.BorderSide(1, "#1d4ed8" if is_active else "#30363d")},
            overlay_color=ft.colors.with_opacity(0.12, "#3b82f6"),
        )

    def _on_tf(tf: str):
        def _handler(e):
            settings["timeframe"] = tf
            save_settings(settings)
            _refresh_tf_buttons()
            load_render()
        return _handler

    tf_btns = [
        ft.ElevatedButton(
            text=tf,
            key=f"tf_{tf}",
            style=_tf_style(tf == settings["timeframe"]),
            on_click=_on_tf(tf),
        )
        for tf in TFS
    ]
    tf_row = ft.Row(tf_btns, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=3)

    def _refresh_tf_buttons():
        for btn in tf_btns:
            btn.style = _tf_style(btn.text == settings["timeframe"])
        page.update()

    # ── Indicator buttons ───────────────────
    def _ind_style(ind_id: str) -> ft.ButtonStyle:
        cfg       = INDICATOR_CONFIG[ind_id]
        is_active = ind_id in settings["active_indicators"]
        c         = cfg["color"]
        return ft.ButtonStyle(
            bgcolor={"": ft.colors.with_opacity(0.12, c) if is_active else "#21262d"},
            color={"":   c if is_active else "#8b949e"},
            side={"":    ft.BorderSide(1, c if is_active else "#30363d")},
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
            shape=ft.RoundedRectangleBorder(radius=6),
        )

    def _on_ind(ind_id: str):
        def _handler(e):
            if ind_id in settings["active_indicators"]:
                settings["active_indicators"].remove(ind_id)
            else:
                settings["active_indicators"].append(ind_id)
            save_settings(settings)
            _refresh_ind_buttons()
            load_render()
        return _handler

    def _ind_label(ind_id: str) -> str:
        cfg       = INDICATOR_CONFIG[ind_id]
        is_active = ind_id in settings["active_indicators"]
        return ("✓ " if is_active else "") + cfg["name"]

    ind_btns = [
        ft.ElevatedButton(
            text=_ind_label(k),
            key=f"ind_{k}",
            style=_ind_style(k),
            on_click=_on_ind(k),
        )
        for k in INDICATOR_CONFIG
    ]

    def _refresh_ind_buttons():
        for btn in ind_btns:
            k        = btn.key.replace("ind_", "")
            btn.text  = _ind_label(k)
            btn.style = _ind_style(k)
        page.update()

    ind_grid = ft.GridView(
        controls=ind_btns,
        runs_count=3,
        max_extent=130,
        child_aspect_ratio=2.8,
        spacing=5,
        run_spacing=5,
        height=100,
    )

    # ──────────────────────────────────────
    #  PAGE LAYOUT
    # ──────────────────────────────────────
    def _section(content, pad=ft.padding.symmetric(horizontal=14, vertical=8),
                 border_bottom=True):
        return ft.Container(
            content=content,
            padding=pad,
            bgcolor="#161b22",
            border=ft.border.only(
                bottom=ft.BorderSide(1, "#30363d") if border_bottom else None
            ),
        )

    page.add(
        ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            controls=[
                # ── HEADER ──────────────────────────
                _section(
                    ft.Row([
                        ft.Row([
                            ft.Text("⚡ QUANTUM", size=17, weight=ft.FontWeight.W_800, color="#e6edf3"),
                            ft.Text("TRADER",     size=17, weight=ft.FontWeight.W_800, color="#3b82f6"),
                        ], spacing=3),
                        ft.Row([loading_ring, ft.Text("Python Engine v1.0", size=10, color="#8b949e")], spacing=6),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    pad=ft.padding.symmetric(horizontal=14, vertical=10),
                ),

                # ── PRICE ───────────────────────────
                _section(ft.Row([
                    ft.Column([symbol_label, price_text], spacing=1),
                    change_text,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),

                # ── STATS BAR ───────────────────────
                _section(ft.Row(
                    [stat_h, stat_l, stat_v, stat_t, stat_c],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=14,
                ), pad=ft.padding.symmetric(horizontal=14, vertical=5)),

                # ── TIMEFRAME SWITCHER ───────────────
                ft.Container(
                    content=tf_row,
                    padding=ft.padding.symmetric(horizontal=14, vertical=7),
                    bgcolor="#0d1117",
                ),

                # ── CHART ────────────────────────────
                chart_box,

                # ── INDICATORS ──────────────────────
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 المؤشرات", size=11, color="#8b949e",
                                weight=ft.FontWeight.W_600),
                        ind_grid,
                    ], spacing=6),
                    padding=ft.padding.symmetric(horizontal=14, vertical=8),
                    bgcolor="#0d1117",
                ),

                # ── RSI PANEL ───────────────────────
                _section(ft.Column([
                    ft.Text("📈 RSI (14)", size=11, color="#8b949e",
                            weight=ft.FontWeight.W_600),
                    ft.Row([rsi_val_text, rsi_lbl_text, ema20_text], spacing=14),
                ], spacing=5), border_bottom=False),

                # ── BOTTOM BAR ──────────────────────
                _section(
                    ft.Row([
                        ft.Text("⚡ Quantum Trader", size=10, color="#8b949e"),
                        time_text,
                        src_text,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    pad=ft.padding.symmetric(horizontal=14, vertical=7),
                    border_bottom=False,
                ),
            ],
        )
    )

    # ── Initial data load ───────────────────
    load_render()

    # ── Auto-refresh every 30 s ─────────────
    def _auto_refresh():
        while True:
            time.sleep(30)
            load_render()

    threading.Thread(target=_auto_refresh, daemon=True, name="auto-refresh").start()


# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    ft.app(target=main)
