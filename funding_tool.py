from __future__ import annotations

import argparse
import asyncio
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import sys

import lighter

DEFAULT_MAINNET = "https://mainnet.zklighter.elliot.ai"
DEFAULT_TESTNET = "https://testnet.zklighter.elliot.ai"


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "-").replace("_", "-")


def compact_symbol(symbol: str) -> str:
    return "".join(ch for ch in symbol if ch.isalnum()).upper()


def format_percent(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


async def resolve_market_id(api_client: lighter.ApiClient, symbol: str) -> int:
    order_api = lighter.OrderApi(api_client)
    response = await order_api.order_book_details(market_id=255)
    details = getattr(response, "order_book_details", None) or []

    if not details:
        raise RuntimeError("No market details returned; cannot resolve symbol to market_id.")

    normalized = normalize_symbol(symbol)
    compact = compact_symbol(symbol)

    for item in details:
        item_symbol = getattr(item, "symbol", "")
        if normalize_symbol(item_symbol) == normalized:
            return int(getattr(item, "market_id"))

    for item in details:
        item_symbol = getattr(item, "symbol", "")
        if compact_symbol(item_symbol) == compact:
            return int(getattr(item, "market_id"))

    available = ", ".join(sorted(normalize_symbol(getattr(d, "symbol", "")) for d in details))
    raise RuntimeError(f"Symbol not found: {symbol}. Available symbols: {available}")


async def fetch_funding_total(symbol: str, days: int, host: str) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    end_dt = dt.datetime(now.year, now.month, now.day, tzinfo=dt.timezone.utc)
    end_ts = int(end_dt.timestamp())
    start_ts = end_ts - days * 24 * 60 * 60
    count_back = days * 24

    configuration = lighter.Configuration(host=host)
    async with lighter.ApiClient(configuration) as api_client:
        market_id = int(symbol) if symbol.isdigit() else await resolve_market_id(api_client, symbol)
        candlestick_api = lighter.CandlestickApi(api_client)
        response = await candlestick_api.fundings(
            market_id=market_id,
            resolution="1h",
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            count_back=count_back,
        )

    fundings = getattr(response, "fundings", None) or []
    total_rate = Decimal("0")
    used = 0
    rates_output: list[str] = []

    for item in fundings:
        rate = getattr(item, "rate", None)
        if rate is None:
            continue
        try:
            rate_value = Decimal(str(rate))
            direction = str(getattr(item, "direction", "")).lower()
            if direction == "long":
                rate_value = rate_value
            elif direction == "short":
                rate_value = -rate_value
            total_rate += rate_value
            used += 1
            if days == 7:
                rates_output.append(f"{rate_value}")
        except Exception:
            continue

    start_dt = dt.datetime.fromtimestamp(start_ts, dt.timezone.utc)

    print(f"币对: {normalize_symbol(symbol)}")
    print(f"市场ID: {market_id}")
    print(f"时间范围(UTC): {start_dt} -> {end_dt}")
    print(f"资金费率条数: {used} / {len(fundings)}")
    print(f"累计资金费率: {format_percent(total_rate)}%")
    if days == 7:
        print("资金费率列表:")
        for value in rates_output:
            print(value)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query cumulative funding rate for a symbol over the past N days on Lighter.",
    )
    parser.add_argument("symbol", help="Trading pair symbol, e.g. BTC-USD")
    parser.add_argument("days", type=int, help="Number of past days to include")
    parser.add_argument(
        "--host",
        default=DEFAULT_MAINNET,
        help=f"API host (default: {DEFAULT_MAINNET})",
    )
    parser.add_argument(
        "--testnet",
        action="store_true",
        help="Use Lighter testnet host",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    args = parse_args(argv)
    if args.days <= 0:
        print("days must be a positive integer", file=sys.stderr)
        return 2

    host = DEFAULT_TESTNET if args.testnet else args.host

    try:
        asyncio.run(fetch_funding_total(args.symbol, args.days, host))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
