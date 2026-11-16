
from datetime import datetime, timezone


def analyze_daily_range(symbol, candles, current_price):

    if not candles or len(candles) < 1:
        return None

    now = datetime.now(timezone.utc)

    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    today_start_ms = int(
        today_start.timestamp() * 1000
    )

    # Find yesterday's fully closed daily candle
    previous_candles = [
        candle for candle in candles
        if int(candle[0]) < today_start_ms
    ]

    if not previous_candles:
        return None

    candle = max(
        previous_candles,
        key=lambda item: int(item[0])
    )

    high = float(candle[2])
    low = float(candle[3])
    price = float(current_price)

    daily_range = high - low

    if daily_range <= 0:
        return None

    position = (
        (price - low) / daily_range
    ) * 100

    if position < 0:
        zone = "BELOW_LOW"

    elif position > 100:
        zone = "ABOVE_HIGH"

    elif position <= 10:
        zone = "BOTTOM"

    elif position >= 90:
        zone = "TOP"

    else:
        return None

    distance_from_high = (
        (price - high) / high
    ) * 100

    distance_from_low = (
        (low - price) / low
    ) * 100

    return {
        "symbol": symbol,
        "price": price,
        "yesterday_high": high,
        "yesterday_low": low,
        "position": round(position, 2),
        "zone": zone,
        "distance_from_high": round(distance_from_high, 3),
        "distance_from_low": round(distance_from_low, 3)
    }