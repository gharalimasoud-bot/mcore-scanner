
import asyncio
import httpx
import time

BASE_URL = "https://api.toobit.com"

CONCURRENCY = 5
CANDLE_LIMIT = 20


async def get_contracts(client):
    url = f"{BASE_URL}/api/v1/exchangeInfo"

    response = await client.get(url)
    response.raise_for_status()

    data = response.json()

    contracts = data.get("contracts", [])

    active = [
        item["symbol"]
        for item in contracts
        if item.get("quoteAsset") == "USDT"
        and item.get("marginToken") == "USDT"
        and item.get("status") == "TRADING"
        and item.get("inverse") is False
    ]

    return active


async def scan_symbol(client, symbol, semaphore, now_ms):

    async with semaphore:
        try:
            url = f"{BASE_URL}/quote/v1/klines"

            params = {
                "symbol": symbol,
                "interval": "1m",
                "limit": CANDLE_LIMIT
            }

            response = await client.get(
                url,
                params=params
            )

            response.raise_for_status()

            candles = response.json()

            # Only use fully closed candles
            closed = [
                c for c in candles
                if int(c[0]) + 60000 <= now_ms
            ]

            closed.sort(key=lambda x: int(x[0]))

            if len(closed) < 15:
                return None

            last_15 = closed[-15:]

            start_price = float(last_15[0][1])
            end_price = float(last_15[-1][4])

            if start_price <= 0:
                return None

            change = (
                (end_price - start_price)
                / start_price
            ) * 100

            return {
                "symbol": symbol,
                "change": change,
                "price": end_price,
                "start_price": start_price
            }

        except Exception:
            return None


async def main():

    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=20
    ) as client:

        print("\nConnecting to Toobit...")

        symbols = await get_contracts(client)

        print(f"Active contracts: {len(symbols)}")
        print("Scanning market...\n")

        now_ms = int(time.time() * 1000)

        tasks = [
            scan_symbol(
                client,
                symbol,
                semaphore,
                now_ms
            )
            for symbol in symbols
        ]

        results = await asyncio.gather(*tasks)

        valid = [
            item for item in results
            if item is not None
        ]

        gainers = sorted(
            valid,
            key=lambda x: x["change"],
            reverse=True
        )

        losers = sorted(
            valid,
            key=lambda x: x["change"]
        )

        print("=" * 65)
        print(f"SCAN COMPLETE | {len(valid)}/{len(symbols)}")
        print("=" * 65)

        print("\nTOP 10 GAINERS")
        print("-" * 65)

        for item in gainers[:10]:
            print(
                f'{item["symbol"]:<22} '
                f'{item["change"]:>+9.3f}% '
                f'Price: {item["price"]}'
            )

        print("\nTOP 10 LOSERS")
        print("-" * 65)

        for item in losers[:10]:
            print(
                f'{item["symbol"]:<22} '
                f'{item["change"]:>+9.3f}% '
                f'Price: {item["price"]}'
            )

        print("\nFailed requests:", len(symbols) - len(valid))


if __name__ == "__main__":
    asyncio.run(main())
