
import asyncio
import httpx
import time
from datetime import datetime, timezone, timedelta

from scanner import get_contracts
from daily_range import analyze_daily_range

BASE_URL = "https://api.toobit.com"
CONCURRENCY = 5


async def get_all_prices(client):
    url = f"{BASE_URL}/quote/v1/contract/ticker/price"

    response = await client.get(url)
    response.raise_for_status()

    data = response.json()

    return {
        item["s"]: float(item["p"])
        for item in data
    }


async def scan_test_symbol(client, symbol, semaphore, prices, now_ms):

    async with semaphore:
        try:
            today = datetime.now(timezone.utc).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )

            yesterday = today - timedelta(days=1)

            params = {
                "symbol": symbol,
                "interval": "1d",
                "startTime": int(yesterday.timestamp() * 1000),
                "endTime": now_ms,
                "limit": 2
            }

            response = await client.get(
                f"{BASE_URL}/quote/v1/klines",
                params=params
            )

            response.raise_for_status()

            candles = response.json()

            price = prices.get(symbol)

            if price is None:
                return None

            return analyze_daily_range(
                symbol,
                candles,
                price
            )

        except Exception as error:
            print(f"ERROR {symbol}: {error}")
            return None


async def main():

    async with httpx.AsyncClient(timeout=30) as client:

        print("\nConnecting to Toobit...")

        symbols = await get_contracts(client)

        print("Active contracts:", len(symbols))

        print("Receiving latest prices...")

        prices = await get_all_prices(client)

        print("Received prices:", len(prices))

        test_symbols = symbols[:5]

        print("\nTesting symbols:")
        print(test_symbols)

        semaphore = asyncio.Semaphore(CONCURRENCY)

        now_ms = int(time.time() * 1000)

        tasks = [
            scan_test_symbol(
                client,
                symbol,
                semaphore,
                prices,
                now_ms
            )
            for symbol in test_symbols
        ]

        results = await asyncio.gather(*tasks)

        valid = [item for item in results if item is not None]

        print("\n" + "=" * 65)
        print("DAILY RANGE TEST")
        print("=" * 65)

        print("Tested:", len(test_symbols))
        print("Matched zones:", len(valid))

        for item in valid:

            print(
                f'\n{item["symbol"]}'
                f'\nZone: {item["zone"]}'
                f'\nPrice: {item["price"]}'
                f'\nYesterday High: {item["yesterday_high"]}'
                f'\nYesterday Low: {item["yesterday_low"]}'
                f'\nPosition: {item["position"]}%'
            )

        print("\nTEST FINISHED")


if __name__ == "__main__":
    asyncio.run(main())
