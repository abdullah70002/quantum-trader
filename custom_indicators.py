"""
╔═══════════════════════════════════════════════════════╗
║   QUANTUM TRADER - قالب لإضافة مؤشراتك الخاصة       ║
║   ضع هذا الملف في نفس مجلد app.py                   ║
╚═══════════════════════════════════════════════════════╝

كيفية الاستخدام:
1. انسخ أحد الأمثلة أدناه
2. أضف دالتك في class IndicatorEngine في app.py
3. أضف الإعداد في قاموس INDICATOR_CONFIG
4. شغل التطبيق واضغط على المؤشر في الواجهة

قالب الدالة:
  @staticmethod
  def MY_INDICATOR(df: pd.DataFrame, period: int = 14) -> pd.Series:
      # df يحتوي على: time, open, high, low, close, volume
      result = ... # احسب قيمتك هنا
      return result  # يجب أن يكون pd.Series بنفس طول df
"""

import pandas as pd
import numpy as np


# ══════════════════════════════════════════════════════════
#  مثال 1: مؤشر Supertrend
# ══════════════════════════════════════════════════════════
def SUPERTREND(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """
    مؤشر Supertrend - يحدد الاتجاه العام
    القيمة = سعر الدعم/المقاومة الحالي
    """
    hl2 = (df["high"] + df["low"]) / 2

    # Average True Range
    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["close"].shift(1))
    tr3 = abs(df["low"] - df["close"].shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=period, adjust=False).mean()

    # Upper & Lower Bands
    upper = hl2 + (multiplier * atr)
    lower = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=df.index, dtype=float)
    direction  = pd.Series(1, index=df.index)

    for i in range(1, len(df)):
        if df["close"].iloc[i] > upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["close"].iloc[i] < lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
            if direction.iloc[i] == 1:
                lower.iloc[i] = max(lower.iloc[i], lower.iloc[i - 1])
            else:
                upper.iloc[i] = min(upper.iloc[i], upper.iloc[i - 1])

        supertrend.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]

    return supertrend


# ══════════════════════════════════════════════════════════
#  مثال 2: مؤشر Stochastic RSI
# ══════════════════════════════════════════════════════════
def STOCH_RSI(df: pd.DataFrame, period: int = 14, smooth_k: int = 3) -> pd.Series:
    """
    Stochastic RSI - أكثر حساسية من RSI العادي
    نطاق القيم: 0 إلى 100
    """
    delta = df["close"].diff()
    gain  = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rsi   = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    rsi_min = rsi.rolling(window=period).min()
    rsi_max = rsi.rolling(window=period).max()

    stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)) * 100
    return stoch_rsi.rolling(window=smooth_k).mean()


# ══════════════════════════════════════════════════════════
#  مثال 3: مؤشر Hull Moving Average (HMA)
# ══════════════════════════════════════════════════════════
def HMA(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Hull Moving Average - أسرع وأنعم من EMA
    يقلل التأخر بشكل كبير
    """
    half_period = period // 2
    sqrt_period = int(np.sqrt(period))

    wma_half = df["close"].rolling(half_period).apply(
        lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum()
    )
    wma_full = df["close"].rolling(period).apply(
        lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum()
    )
    raw = 2 * wma_half - wma_full
    hma = raw.rolling(sqrt_period).apply(
        lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.arange(1, len(x) + 1).sum()
    )
    return hma


# ══════════════════════════════════════════════════════════
#  مثال 4: مؤشر Ichimoku - الخط الأول (Tenkan-sen)
# ══════════════════════════════════════════════════════════
def ICHIMOKU_TENKAN(df: pd.DataFrame, period: int = 9) -> pd.Series:
    """خط التحويل في Ichimoku - (أعلى + أدنى) / 2 خلال 9 فترات"""
    return (df["high"].rolling(period).max() + df["low"].rolling(period).min()) / 2


def ICHIMOKU_KIJUN(df: pd.DataFrame, period: int = 26) -> pd.Series:
    """خط القاعدة في Ichimoku - (أعلى + أدنى) / 2 خلال 26 فترة"""
    return (df["high"].rolling(period).max() + df["low"].rolling(period).min()) / 2


# ══════════════════════════════════════════════════════════
#  كيفية إضافة مؤشر جديد إلى app.py
# ══════════════════════════════════════════════════════════
"""
الخطوة 1: أضف الدالة في IndicatorEngine class:

    @staticmethod
    def SUPERTREND(df, period=10, multiplier=3.0):
        # انسخ كود الدالة من هنا
        ...

الخطوة 2: أضف في INDICATOR_CONFIG:

    "SUPERTREND": {
        "func": "SUPERTREND",
        "params": {"period": 10, "multiplier": 3.0},
        "color": "#f59e0b",
        "name": "Supertrend"
    },

الخطوة 3: شغل التطبيق وسيظهر المؤشر في قائمة المؤشرات ✓
"""
