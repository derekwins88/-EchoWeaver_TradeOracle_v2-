.PHONY: validate-io
validate-io:
	python scripts/validate_io.py --schema common/schema/brain.signal.json --file samples/brain_signals.ndjson
	python scripts/validate_io.py --schema common/schema/oracle.trade_event.json --file samples/trade_events.ndjson
	python scripts/validate_io.py --schema common/schema/oracle.strategy_return.json --file samples/strategy_returns.ndjson
	python scripts/validate_io.py --schema common/schema/portfolio.allocation.json --file samples/portfolio_allocation.json

.PHONY: io-validate io-summarize test
io-validate:
	python scripts/io_cli.py validate --kind signals --path samples/brain_signals.ndjson
	python scripts/io_cli.py validate --kind events  --path samples/trade_events.ndjson
	python scripts/io_cli.py validate --kind returns --path samples/strategy_returns.ndjson
	python scripts/io_cli.py validate --kind alloc   --path samples/portfolio_allocation.json

io-summarize:
	python scripts/io_cli.py summarize --kind returns --path samples/strategy_returns.ndjson
	python scripts/io_cli.py summarize --kind events  --path samples/trade_events.ndjson

test:
	pytest -q
