Lighter Funding Rate Tool

Overview
- CLI tool to query cumulative funding rates for a symbol over the past N days.
- Uses the official lighter-python SDK (module name: lighter).

Setup
1) Create a venv (optional):
   python -m venv .venv
   .venv\Scripts\activate
2) Install dependencies:
   pip install -r requirements.txt

Usage
- Mainnet (default):
  python funding_tool.py BTC-USD 7
- Testnet:
  python funding_tool.py BTC-USD 7 --testnet
- Custom host:
  python funding_tool.py BTC-USD 7 --host https://mainnet.zklighter.elliot.ai

Notes
- Symbol lookup uses orderBookDetails to map symbol -> market_id.
- Funding resolution is fixed to 1h (the only supported resolution).
# lighter-fundingrate-tool
