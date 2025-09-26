# Vocabulary Map (Brain ⇌ TradeOracle ⇌ Entropy-Portfolio)

| Concept / Field       | Brain (signals / capsules) | TradeOracle (strategy / execution) | Entropy-Portfolio-Lab (allocation / risk) | **Preferred** |
|---|---|---|---|---|
| Uncertainty / Risk    | confidence, entropy_score  | entropy_gate, regime_entropy        | entropy_risk, entropy_metric               | **entropy_score** (0–1) |
| State / Mode          | capsule_state, claim_status| regime_state, motif_flag            | portfolio_state                             | **regime_state** (enum) |
| Signal Strength       | activation, confidence     | conviction, motif_strength          | —                                          | **confidence** (0–1) |
| Structural Unit       | capsule, statement, note   | motif, glyph, trade_rule            | portfolio_block, weight_vector              | **capsule** (research), **motif** (trading) |
| Event                 | signal_timestamp           | trade_event, execution_time         | rebalance_time                              | **timestamp** (ISO-8601) |
| Output                | capsule.json               | trade_log.csv                       | weights.csv                                  | **Unified I/O** (JSON/CSV + hash) |
| Performance Metric    | —                          | pnl_curve, ROI_scorer, drawdown     | entropy_diversification, expected_return     | **pnl_curve, drawdown, sharpe** |
| Capital Unit          | —                          | position_size, risk_unit            | weight, allocation                           | **weight** (0–1) |
| Check / Guard         | assumptions, proof_guard   | risk_gate, entropy_gate             | constraint, bound                            | **constraint** (general), **risk_gate** (execution) |
| Provenance            | hash, capsule_id           | trade_id, hash_chain                | portfolio_id                                 | **id + hash** (chainable) |

**Notes**
- Use `entropy_score` everywhere for uncertainty/risk (0–1).
- Use `regime_state` for modes (e.g., `flat`, `trend_up`, `trend_down`, `volatile`, `collapsing`, `recovering`).
- Standardize `timestamp` as ISO-8601 UTC (`Z`).
- Normalize all portfolio capital fields as `weight` in `[0,1]` (sum to 1.0).
