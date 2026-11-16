
import asyncio
import httpx
import time

from datetime import datetime, timezone

from scanner import get_contracts
from daily_range import analyze_daily_range


BASE_URL = "https://api.toobit.com"

CONCURRENCY = 8

# Daily candle cache
CANDLE_CACHE = {}
CACHE_DATE = None


async def get_all_prices(client):

    url = f"{BASE_URL}/quote/v1/contract/ticker/price"

    response = await client.get(url)
    response.raise_for_status()

    data = response.json()

    return {
        item["s"]: float(item["p"])
        for item in data
    }


async def get_daily_candles(
    client,
    symbol,
    semaphore,
    today_start_ms,
    now_ms
):

    global CACHE_DATE

    if symbol in CANDLE_CACHE:
        return CANDLE_CACHE[symbol]

    async with semaphore:

        url = f"{BASE_URL}/quote/v1/klines"

        yesterday_start_ms = today_start_ms - 86400000

        params = {
            "symbol": symbol,
            "interval": "1d",
            "startTime": yesterday_start_ms,
            "endTime": now_ms,
            "limit": 2
        }

        response = await client.get(
            url,
            params=params
        )

        response.raise_for_status()

        candles = response.json()

        if not candles:
            return None

        CANDLE_CACHE[symbol] = candles

        return candles


async def scan_daily_symbol(
    client,
    symbol,
    semaphore,
    prices,
    today_start_ms,
    now_ms
):

    try:

        price = prices.get(symbol)

        if price is None:
            return None, False

        candles = await get_daily_candles(
            client,
            symbol,
            semaphore,
            today_start_ms,
            now_ms
        )

        if not candles:
            return None, False

        result = analyze_daily_range(
            symbol,
            candles,
            price
        )

        return result, True

    except Exception as error:

        print(f"ERROR {symbol}: {error}")

        return None, False


async def scan_daily_market():

    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        print("Connecting to Toobit...")

        symbols = await get_contracts(client)

        print("Active contracts:", len(symbols))

        prices = await get_all_prices(client)

        print("Received prices:", len(prices))

        now_ms = int(time.time() * 1000)

        today_start = datetime.now(
            timezone.utc
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        today_start_ms = int(
            today_start.timestamp() * 1000
        )

        global CACHE_DATE

        current_date = today_start.date()

        if CACHE_DATE != current_date:
            CANDLE_CACHE.clear()
            CACHE_DATE = current_date

        print("Scanning daily candles...")

        tasks = [
            scan_daily_symbol(
                client,
                symbol,
                semaphore,
                prices,
                today_start_ms,
                now_ms
            )
            for symbol in symbols
        ]

        results = await asyncio.gather(*tasks)

    matches = []
    scanned = 0

    for result, success in results:

        if success:
            scanned += 1

        if result is not None:
            matches.append(result)

    top = [
        item for item in matches
        if item["zone"] == "TOP"
    ]

    bottom = [
        item for item in matches
        if item["zone"] == "BOTTOM"
    ]

    above = [
        item for item in matches
        if item["zone"] == "ABOVE_HIGH"
    ]

    below = [
        item for item in matches
        if item["zone"] == "BELOW_LOW"
    ]

    top.sort(
        key=lambda x: x["position"],
        reverse=True
    )

    bottom.sort(
        key=lambda x: x["position"]
    )

    above.sort(
        key=lambda x: x["distance_from_high"]
    )

    below.sort(
        key=lambda x: x["distance_from_low"]
    )

    return {
        "total_contracts": len(symbols),
        "scanned": scanned,
        "failed": len(symbols) - scanned,
        "price_count": len(prices),
        "matched": len(matches),
        "top": top,
        "bottom": bottom,
        "above_high": above,
        "below_low": below,
        "results": matches
    }
