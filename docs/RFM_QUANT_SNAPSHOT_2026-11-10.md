# RFM Quant — snapshot histórico experimental (10-11-2026)

## Resultados provisórios: não equivalem à estratégia final
A RFM confirmada requer Fibonacci Gold Zone 67–75%, FVG na zona e zonas relevantes de liquidez estrutural (EQH/EQL, BSL/SSL, máximos/mínimos anteriores). BOS e POC são confluências opcionais. Não se utilizou nenhum critério retirado de vídeos.

**O gerador experimental atual ainda exige BOS** e não impõe um limiar de relevância estrutural da liquidez aprovado pelo utilizador. Estes resultados NÃO medem a rentabilidade validada da sua RFM.

## Histórico e parâmetros
Foram usadas 4 000 velas históricas OKX confirmadas por instrumento de 15m: BTC-USDT-SWAP e ETH-USDT-SWAP; período UTC de 30-09-2026 04:00 até 10-11-2026 19:45 (8 000 velas no total). Dados descarregados via API read-only e registados em artefactos CSV/JSON.

Hipóteses de simulação: Fibonacci entrada 75%, validade da ordem de 8 velas, SL no 100%, TP no 0%, risco-alvo 1%, exposição máxima 1x, taxa 5 bps/lado, slippage 2 bps/lado, tempo máximo em posição de 96 velas. Não inclui funding, impacto de mercado ou tamanho real do livro de ordens.

| Métrica | BTC | ETH |
|---|---:|---:|
| Candidatos com FVG ativo na Gold Zone | 14 | 14 |
| Operações concluídas | 2 | 1 |
| Entradas não preenchidas | 12 | 13 |
| Trades positivos observados | 2 | 1 |
| Expectativa observada | +0,346R | +1,104R |
| Retorno simulado | +0,6932% | +1,1041% |
| POC OHLCV aproximado na Gold Zone | 2/14 | 2/14 |
| XGBoost walk-forward | Amostra insuficiente | Amostra insuficiente |

Amostra de apenas **três trades**, insuficiente para determinar win rate estável, desempenho de XGBoost ou edge estatístico.

### Sensibilidade de toque: 28 sinais iguais
Esta análise mede somente a passagem do preço pelo nível: não reexecuta o backtester, não verifica se FVG continua válido e não mede PnL.

| Entrada | 8 velas (2h) | 32 velas (8h) |
|---|---:|---:|
| Fibonacci 67% | 10/28 (35,7%) | 20/28 (71,4%) |
| Fibonacci 75% | 3/28 (10,7%) | 17/28 (60,7%) |

A entrada e o tempo de validade afetam drasticamente o número de toques. Estes valores não justificam otimização nem alteração das regras sem validação fora da amostra.

## Código e dados
- [Workflow do histórico público e artefactos CSV/JSON](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/actions/runs/42892213487)
- [Exportação histórica até 20 000 velas](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/research/export_research.py)
- [Análise reproduzível da sensibilidade de toque](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/research/entry_sensitivity.py)
- [Pandas/NumPy/XGBoost walk-forward com purga temporal](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/research/quant_pipeline.py)

## Passos para um backtest fiel
Definir o modo objetivo de escolher âncoras da Fibonacci; formalizar relevância da liquidez estrutural sem olhar para resultados futuros; reconhecer setups também sem BOS; especificar invalidações de FVG, ordens e custos. Recolher amostra grande de diferentes ativos e regimes, reservar teste cronológico intocado e só então avaliar quantitativamente as confluências e o XGBoost.
