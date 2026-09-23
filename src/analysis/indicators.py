import pandas as pd


def add_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df = df.copy()
    df[f"SMA_{period}"] = df["close"].rolling(window=period).mean()
    return df
