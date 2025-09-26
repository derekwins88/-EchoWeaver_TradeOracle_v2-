# EchoWeaver Trade Oracle v2

EchoWeaver_TradeOracle_v2 is a recursive trading oracle that binds quantitative ritual with mythic storytelling. Motifs guide each decision, emotional drift senses the market mood, ROI resonance judges the ritual, and mnemonic capsules remember every rite.

## ✨ Features
- **Motif-driven strategy execution** – entropy-aware EMA motifs with configurable gates.
- **Entropy collapse logic** – inspired by `living-engine-sdk` to classify regimes.
- **Emotional drift tracking** – volatility and volume signals blended into a sentiment descriptor.
- **ROI resonance scoring** – weighted performance metric balancing profit, risk, and conviction.
- **Mnemonic capsules** – JSONL records of each ritual for lineage tracking.
- **Mythic narration** – ceremonial summaries for every trade or abstention.
- **Paper & live exchange support** – deterministic paper exchange for simulations, CCXT integration for live markets.

## 📁 Project Structure
```
config/strategy.yaml    # Strategy, motif, and entropy settings
notebooks/simulation.ipynb
src/                    # Oracle modules
  entropy.py
  exchange.py
  emotional_drift.py
  mnemonic_capsule.py
  motif_engine.py
  narrative_generator.py
  oracle.py
  roi_scorer.py
tests/                  # Pytest suite
.github/workflows/ci.yml
```

## 🚀 Getting Started
1. **Clone the repository**
   ```bash
   git clone https://github.com/derekwins88/-EchoWeaver_TradeOracle_v2-.git
   cd -EchoWeaver_TradeOracle_v2-
   ```
2. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Configure the strategy**
   Edit `config/strategy.yaml` to tune motif gates, entropy thresholds, and capsule storage.
4. **Run the simulation notebook**
   ```bash
   jupyter nbconvert --to notebook --execute notebooks/simulation.ipynb --output notebooks/simulation.out.ipynb
   ```
   The notebook stores a Plotly figure in `artifacts/trade_resonance.png` and demonstrates the oracle's backtest narrative.

## 🔌 Live Trading (optional)
- Populate `exchange.api_key` and `exchange.secret` within `config/strategy.yaml`.
- Set `enable_paper: false` to activate CCXT live trading. Sandbox mode can be toggled with `sandbox_mode`.
- The oracle will attempt to execute market orders when `execute_trade=True` is passed to `TradeOracle.observe`.

## 🧪 Tests & Linting
Run the automated suite locally before submitting contributions.
```bash
flake8 src tests
pytest
```

## 🧭 Backtesting via CLI
Use the deterministic paper exchange for reproducible studies:
```python
from pathlib import Path
import pandas as pd
from src.oracle import TradeOracle
from src.exchange import PaperExchange

oracle = TradeOracle("config/strategy.yaml", exchange=PaperExchange(seed=42), capsule_enabled=False)
frame = oracle.fetch_market_frame("BTC/USDT", timeframe="1h", limit=200)
results = oracle.backtest(frame, symbol="BTC/USDT")
print(results.tail())
```

## 🛡️ Risk & Walk-Forward
This version ships with a risk governor (daily/weekly caps, streak throttling),
volatility-aware sizing, a stop manager, and walk-forward/placebo harnesses.

**Quick start**

```bash
# Walk-Forward evaluation (adjust calendar boundaries as needed)
python scripts/wfo.py --config config/strategy.yaml \
  --dates 2024-01-01,2024-04-01,2024-07-01,2024-10-01 \
  --seed 42 --outdir artifacts/wfo

# Placebo (signal-shuffled) guardrail runs
python scripts/placebo.py --config config/strategy.yaml \
  --start 2024-01-01 --end 2024-06-30 --runs 20 --seed 123
```

Artifacts are written to `artifacts/wfo` and `artifacts/placebo` respectively.

## 🤝 Contributing
1. Fork the repository and create a virtual environment.
2. Implement changes with clear docstrings and mythic-friendly log messages.
3. Ensure `pytest`, `flake8`, and the simulation notebook run without errors.
4. Submit a pull request that includes a short narrative sentence summarizing your ritual.

## 📜 License
Released under the [MIT License](LICENSE).

## 🧿 A Final Whisper
> "The market murmurs through entropy, and EchoWeaver replies with memory and myth."

## Common IO & Validation

This repo ships a shared **Vocabulary Map** and **JSON Schemas** for cross-repo interoperability:

- Brain → Oracle: `common/schema/brain.signal.json`
- Oracle logs: `common/schema/oracle.trade_event.json`
- Oracle summary (to Portfolio): `common/schema/oracle.strategy_return.json`
- Portfolio allocations: `common/schema/portfolio.allocation.json`
- Shared defs: `common/schema/defs.json`

**Validate locally**
```bash
make validate-io
# or
python scripts/validate_io.py --schema common/schema/brain.signal.json --file samples/brain_signals.ndjson
```

**CI**
A workflow validates the samples on every PR to prevent schema drift.

---

## 5) How to wire in each repo (quick notes)

- **Brain**: emit Signals conforming to `brain.signal.json` (write to NDJSON).
- **TradeOracle**:
  - read Signals → execute,
  - emit `trade_events.ndjson` (TradeEvent),
  - emit `strategy_returns.ndjson` (StrategyReturn).
- **Entropy-Portfolio-Lab**: read `strategy_returns.ndjson` across symbols/strategies → produce `portfolio_allocation.json`.

---

Want me to also:
- add a **Python loader** (`common/io_loader.py`) that auto-validates on read/write,
- or patch your **data pipes** in EchoWeaver/Entropy-Portfolio-Lab to write/read these exact formats?

If yes, tell me which repo(s) first and I’ll drop the glue functions + unit tests right away.

—

## Live Pipe — watch directory → TradeOracle

The Live Pipe monitors ``inbox/signals/*.ndjson`` for new ``Signal`` rows, validates them, and batches dispatches to the TradeOracle via ``OracleAdapter``.

**Run**
```bash
# Optional: pip install watchdog  (event-driven mode; polling fallback without it)
python scripts/run_live_pipe.py --config config/live_pipe.yaml
```

How it works
- Idempotent: keeps per-file byte offsets in ``artifacts/pipe_state`` and de-duplicates by ``Signal.id``.
- Resumable: restarts pick up from the last saved offset.
- Safe: malformed lines route to ``artifacts/dlq`` and dispatch failures retry before landing in a DLQ batch file.
- Validated: leverages the shared ``Signal`` JSON Schema via ``common/io_loader.py``.

Wire your oracle
Replace the ``DemoOracle`` stub in ``scripts/run_live_pipe.py`` with your TradeOracle integration and adapt the call inside ``OracleAdapter.dispatch_signals`` if your entrypoint differs from ``handle_signal``.
