# RFM Quant — Quantitative research plan (v1)

## Research objective
**Input → Model → Output → Strategy → Simulated Orders.**
Input: confirmed historical OHLCV, timestamps and instrument metadata.
Model: compute only signal-time-available features (structure, FVG, swing, volatility, volume).
Output: candidate setup and optional predicted probability of positive net R.
Strategy: user-confirmed Fibonacci Gold Zone 67–75%, stop at 100%, target at 0%; optional confluences. Precise automated swing selection remains a **provisional pivot-breakout hypothesis**.
Orders: backtesting only, no exchange order API or account access.

## RFM rules currently supported by the user
- Long: Fibonacci 0% at the upper extreme and 100% at the lower extreme. Short: reverse.
- Entry within 67–75% Gold Zone, stop around 100%, target around 0%.
- **FVG ainda ativo e sobreposto à Gold Zone é essencial.** É também essencial haver **zonas de liquidez estrutural relevantes**: EQH/EQL, BSL/SSL e máximos/mínimos anteriores; a quantidade e o limiar mecânico exatos ainda estão por fixar.
- BOS/CHoCH, sweep, alinhamento 4H e POC não são filtros obrigatórios na RFM do utilizador; tratam-se de confluências/contexto (o BOS é importante, mas opcional).
- POC is optional and uses the range from the Fibonacci anchor candle to the last closed decision candle. Current OHLCV POC is an **approximation**, not true traded volume by price.
- A deteção de FVG já permite simular preenchimento parcial/total de gaps entre três velas; é uma **aproximação de investigação**, não a definição final da validade de um FVG. Âncoras dos swings, entrada exata e stop buffer ainda não estão fechados.

## What the quantitative code actually does
- `research/export_research.py` pagina dados públicos OKX através da API read-only (até **20 000 velas**, se disponíveis, sem preencher intervalos em falta), força FVG ativo sobreposto à Gold Zone, executa o gerador provisório de candidatos e o simulador conservador, grava candles/events/signals/trades/model_dataset em CSV e invoca Pandas/NumPy/XGBoost se houver operações concluídas. Os conjuntos incompletos são assinalados.
- `structural_liquidity.py` calcula features históricas causais de pivôs confirmados BSL/SSL, pares EQH/EQL e máximos/mínimos de dias/semanas UTC **completos**. A tolerância de proximidade e qualquer contagem mínima são apenas hipóteses de investigação; por omissão **não há filtro de quantidade de zonas**.
- `fvg_state.py` mantém apenas a porção ainda não totalmente mitigada de um FVG de três velas na Gold Zone.
- `volume_profile.py` fornece confluência de POC baseada numa aproximação OHLCV, que nunca substitui o volume por preço real.
- **Atenção: `rfm_candidates.py` continua a exigir BOS/pivot breakout como gatilho mecânico, embora o BOS seja opcional na RFM original.** Por isso, os resultados do pipeline são exclusivamente **resultados de uma hipótese provisória**, não resultados comprovados da estratégia do utilizador.
- `research/quant_pipeline.py` calcula features com Pandas/NumPy conhecidas até ao fecho do sinal, pode acrescentar contagens de liquidez/POC quando há dados completos, rotula apenas operações executadas e terminadas e avalia XGBoost em validação walk-forward expansiva. **Training labels must be known (trade exit before test signal).**
- A simple baseline win probability is scored against XGBoost using Brier score. Better Brier score is NOT proof of profit or of a useful trading filter.
- If fewer than 105 labelled closed trades exist at defaults, the walk-forward returns insufficient data. No invented win rate, accuracy or trading performance.
- No tuning on the test folds, no predictions from future candles, no deployment of ML signals to trading.
- A API de produção limita cada pedido a 2 000 velas, mas a exportação de investigação pode fazer paginação até 20 000. Mesmo assim, é necessário auditar mudanças de regime, qualidade, custos e enviesamento de sobrevivência. Os 25+ trades fora da amostra de cada fold não garantem robustez por si só.

## Reproducible run
```bash
pip install -r requirements-research.txt
python -m research.export_research --symbol BTC-USDT-SWAP --bar 15m --bars 10000
jupyter lab notebooks/01_rfm_quant_research.ipynb
```
A exportação guarda `candles.csv`, `events.csv`, `signals.csv`, `trades.csv`, `model_dataset.csv` e `report.json` em `research_outputs/BTC-USDT-SWAP/15m/`. Não há performances inventadas ou predefinidas. A workflow `research-snapshot.yml` recolhe também uma fotografia histórica pública experimental e disponibiliza CSVs como artefactos quando o serviço está acessível.

## Next validation gates
1. Agree on objective swing anchoring and entry rules using the user's annotated historical screenshots.
2. Audit simulator fill behavior, fees, funding and exchange instrument sizing.
3. Gather long-duration timestamped datasets with continuity checks and preserved snapshots.
4. Backtest the frozen strategy across multiple markets and regimes.
5. Use untouched chronological holdouts and walk-forward evaluation; report uncertainty and parameter sensitivity.
6. Only consider paper trading after independent validation. Never auto-submit real orders from the research environment.
