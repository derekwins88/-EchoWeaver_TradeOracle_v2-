.PHONY: validate-io
validate-io:
	python scripts/validate_io.py --schema common/schema/brain.signal.json --file samples/brain_signals.ndjson
	python scripts/validate_io.py --schema common/schema/oracle.trade_event.json --file samples/trade_events.ndjson
	python scripts/validate_io.py --schema common/schema/oracle.strategy_return.json --file samples/strategy_returns.ndjson
	python scripts/validate_io.py --schema common/schema/portfolio.allocation.json --file samples/portfolio_allocation.json
