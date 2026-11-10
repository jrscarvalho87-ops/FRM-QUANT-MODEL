# RFM — Registo de estratégia para investigação (versão 1.0)

**Estado: parcialmente confirmada.** Este documento distingue regras descritas pelo utilizador de decisões técnicas ainda por aprovar. Não substituir a estratégia original por uma estratégia inventada.

## Fluxo
**Input**: OHLCV de contratos perpetual, preços e timestamps, timeframe de execução 15m, contexto 4H; histórico validado, sem velas futuras.
**Modelo quantitativo**: identifica swings, estrutura, desequilíbrios, liquidez e contexto; calcula features; XGBoost apenas para testar se há informação preditiva incremental.
**Output**: candidatos a setup com direção, hora, níveis Fibonacci, contexto e features disponíveis naquele momento.
**Estratégia**: aplica as regras RFM e de gestão de risco.
**Orders**: para já ordens **simuladas** no backtest, não ordens reais enviadas à exchange.

## Regras descritas pelo utilizador
| Elemento | Regra | Estado |
|---|---|---|
| Mercado | Criptomoedas, perpetual futures, ativos variados | Confirmado |
| Timeframes | Execução 15m; contexto 4H | Confirmado nas imagens e configuração RFM |
| Fibonacci long | 0% no topo do movimento, 100% no fundo | Confirmado |
| Fibonacci short | 0% no fundo do movimento, 100% no topo | Confirmado |
| Gold Zone | Retração 67–75% | Confirmado |
| SL | Na região do 100% | Confirmado, buffer exato pendente |
| TP | Na região do 0% | Confirmado, buffer exato pendente |
| FVG / imbalance | Confluência frequentemente observada na Gold Zone | Confirmado como confluência, não filtro universal |
| BOS ou CHoCH | Informação estrutural; CHoCH pode substituir BOS | Confirmado como contexto opcional |
| Liquidity sweep | Confluência opcional | Confirmado |
| 4H premium / discount | Informação de alinhamento | Confirmado; regra de decisão ainda não objetiva |
| Volume Profile | Apenas POC, desde a vela inicial da Fib até à vela atual fechada | Confirmado; POC aproximado se só houver OHLCV |
| Gestão de risco | SL e TP sempre definidos; risco controlado | Confirmado; parâmetros exatos do backtest são pressupostos |

## Hipótese mecânica provisória — NÃO é a estratégia original validada
`rfm_candidates.py` usa pivôs confirmados com 3 velas de cada lado, quebra por fecho, swing mínimo 0,5%, entrada limitada a 75% (ou 67%), expiração de 8 velas. Esta escolha é **uma hipótese de investigação**, não uma decisão do utilizador.

`execution.py` usa capital fictício 10 000 USDT, risco pretendido 1%, limite nocional 1x, taxa 5 bps/lado, slippage 2 bps/lado, stop-first quando a mesma vela toca SL e TP, máximo 96 velas por posição. Não modela funding, liquidação, spreads históricos, impacto ou preenchimentos parciais.

## O que ainda tem de ser definido antes do backtest fiel
1. Critério exato para selecionar as duas âncoras da Fibonacci sem olhar para o futuro.
2. Se se entra no primeiro toque da Gold Zone, no 67%, no 75%, ou mediante confirmação.
3. Se o FVG é necessário em alguma família de setups e quando fica mitigado/inválido.
4. Condições objetivas para aceitar/rejeitar setups no contexto 4H.
5. Se e como o POC influencia a decisão, incluindo tolerância de proximidade.
6. Buffers de stop/TP e tratamento de operações sobrepostas.

## Plano de validação
- Congelar regras antes de medir desempenho.
- Auditar OHLCV e snapshots por ativo e período.
- Calcular métricas do backtest com custos e sem fuga temporal.
- Testar períodos de treino, validação e teste cronologicamente separados.
- Avaliar XGBoost **contra baseline**, com purga por saída das operações.
- Só depois comparar variantes e avaliar robustez entre ativos e regimes.

**Sem resultados de backtest real apresentados neste documento.** O pipeline está preparado; a amostra e as regras finais precisam de ser validadas.
