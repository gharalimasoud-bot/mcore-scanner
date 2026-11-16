
import httpx

BASE_URL = "https://api.toobit.com"


def get_futures_contracts():
    url = f"{BASE_URL}/api/v1/exchangeInfo"

    response = httpx.get(url, timeout=20)
    response.raise_for_status()
    data = response.json()

    contracts = data.get("contracts", [])

    active = [
        item for item in contracts
        if item.get("quoteAsset") == "USDT"
        and item.get("marginToken") == "USDT"
        and item.get("status") == "TRADING"
        and item.get("inverse") is False
    ]

    return active


def test_kline(symbol):
    url = f"{BASE_URL}/quote/v1/klines"

    params = {
        "symbol": symbol,
        "interval": "1m",
        "limit": 20
    }

    response = httpx.get(url, params=params, timeout=20)
    response.raise_for_status()

    return response.json()


def main():
    try:
        contracts = get_futures_contracts()

        print(f"\nActive USDT Futures Contracts: {len(contracts)}")

        print("\nFirst 10 contracts:")
        for contract in contracts[:10]:
            print(contract["symbol"])

        if not contracts:
            print("No active contracts found.")
            return

        symbol = contracts[0]["symbol"]

        print(f"\nTesting 1m candles for {symbol}...")

        candles = test_kline(symbol)

        print(f"Received candles: {len(candles)}")

        print("\nLast 3 candles:")
        for candle in candles[-3:]:
            print({
                "time": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5]
            })

    except Exception as error:
        print("\nERROR:", error)


if __name__ == "__main__":
    main()
