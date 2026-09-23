from src.exchanges import EXCHANGES

from src.exchanges.binance import get_price as binance_price
from src.exchanges.okx import get_price as okx_price
from src.exchanges.bybit import get_price as bybit_price
from src.exchanges.coinbase import get_price as coinbase_price
from src.exchanges.kraken import get_price as kraken_price
from src.exchanges.gate import get_price as gate_price
from src.exchanges.bitget import get_price as bitget_price
from src.exchanges.kucoin import get_price as kucoin_price


PRICE_FUNCTIONS = {
    "binance": binance_price,
    "okx": okx_price,
    "bybit": bybit_price,
    "coinbase": coinbase_price,
    "kraken": kraken_price,
    "gate": gate_price,
    "bitget": bitget_price,
    "kucoin": kucoin_price,
}


def get_all_prices() -> dict[str, float]:
    prices = {}

    for exchange in EXCHANGES:
        try:
            prices[exchange] = PRICE_FUNCTIONS[exchange]()
        except Exception as error:
            prices[exchange] = None
            print(f"{exchange} error: {error}")

    return prices