import pandas as pd


def add_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df = df.copy()
    df[f"SMA_{period}"] = df["close"].rolling(window=period).mean()
    return df


def add_ema(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df = df.copy()
    df[f"EMA_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df = df.copy()

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    df[f"RSI_{period}"] = 100 - (100 / (1 + rs))

    return df


def add_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    df = df.copy()

    fast_ema = df["close"].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df["close"].ewm(span=slow_period, adjust=False).mean()

    df["MACD"] = fast_ema - slow_ema
    df["MACD_Signal"] = df["MACD"].ewm(
        span=signal_period,
        adjust=False
    ).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    return df


def add_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.DataFrame:
    df = df.copy()

    middle = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()

    df[f"BB_Middle_{period}"] = middle
    df[f"BB_Upper_{period}"] = middle + (std_dev * std)
    df[f"BB_Lower_{period}"] = middle - (std_dev * std)

    return df