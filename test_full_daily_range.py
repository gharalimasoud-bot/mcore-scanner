
import asyncio

from daily_range_scanner import scan_daily_market


def print_section(title, items, distance_key=None):

    print("\n" + title)
    print("-" * 60)

    if not items:
        print("No symbols found.")
        return

    for item in items:

        if distance_key:
            distance_text = (
                f"Distance: {item[distance_key]:.3f}%"
            )
        else:
            distance_text = (
                f"Position: {item['position']:.2f}%"
            )

        print(
            f"{item['symbol']:<22} "
            f"Price: {item['price']:<14} "
            f"{distance_text}"
        )


async def main():

    print("M-CORE DAILY RANGE SCANNER")
    print("=" * 60)

    result = await scan_daily_market()

    print("\nSCAN COMPLETE")
    print("=" * 60)

    print("Total contracts:", result["total_contracts"])
    print("Successfully scanned:", result["scanned"])
    print("Failed:", result["failed"])
    print("Matched:", result["matched"])

    print_section(
        "NEAR YESTERDAY HIGH (10%)",
        result["top"]
    )

    print_section(
        "NEAR YESTERDAY LOW (10%)",
        result["bottom"]
    )

    print_section(
        "ABOVE YESTERDAY HIGH",
        result["above_high"],
        "distance_from_high"
    )

    print_section(
        "BELOW YESTERDAY LOW",
        result["below_low"],
        "distance_from_low"
    )


if __name__ == "__main__":
    asyncio.run(main())
