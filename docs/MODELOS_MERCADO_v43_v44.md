# RFM Quant v43–v44 — Tendência, momentum e previsões de direção

**12 novembro 2026 — somente investigação.** Não é automação de ordens, sinal de negociação ou estimativa de win rate RFM.

## Dados
BTCUSDT, ETHUSDT, SOLUSDT, ZECUSDT; 35 040 velas de 15m por ativo (1 nov 2025–31 out 2026), OHLCV histórico Binance USD-M. Total: 140 160 velas.

233 setups RFM candidatos na v38, 14 elegíveis, **2 trades elegíveis resolvidas**. Não existem labels suficientes para classificador de sucesso RFM.

## Features causais v43
Calculadas exclusivamente com velas **fechadas até t-1**, para previsão na abertura t: momentum 1h/4h/24h; spread e inclinação das EMA32/128; efficiency ratio 4h; RSI14; desvio-padrão EWMA; volatilidade relativamente à referência; volume versus média 96 velas.

Regimes descritivos: UP/DOWN/MIXED pelo spread e inclinação da EMA; HIGH/LOW pela volatilidade relativa; momentum ALIGNED/OPPOSED/NEUTRAL. **Nenhum é filtro operacional da RFM.**

## Modelos direcionais v44
Regressão logística regularizada com StandardScaler aplicado somente ao treino, comparada com prevalência histórica nos 90 dias anteriores e benchmark de momentum. Treino móvel mensal de 90 dias; avaliação mar–out 2026; labels futuros purgados na fronteira temporal; previsões de 15m, 1h e 4h em janelas sem sobreposição.

Alvo: retorno seguinte positivo vs. não positivo (retorno zero é não positivo); **não** sucesso da operação RFM.

| Horizonte | Acerto logística | Acerto benchmark | Vantagem Brier vs benchmark |
| --- | ---: | ---: | ---: |
| 15m | 52,38% | 50,39% | +0,000631 |
| 1h | 51,33% | 49,25% | -0,000498 |
| 4h | 51,70% | 49,61% | -0,003875 |

A vantagem de Brier de 15m é pequena; em outubro foi negativa. Bootstrap emparelhado de 36 semanas/5 000 reamostragens dá IC exploratório de 95%: [+0,000125, +0,001076] para a vantagem de 15m. **Não representa lucro nem probabilidade de acertar TP/SL.** Em 1h a vantagem não se confirma, em 4h o Brier piora.

## Cruzamento com setups RFM
105 candidatos com a tendência calculada (4 elegíveis), 80 contra (8), 48 mistos/desconhecidos (2). Com apenas 2 operações resolvidas, não é possível determinar o regime vencedor; não alterar filtros.

## Estado e próximos passos
- Código, CSV de resultados, 15 testes automáticos e manifesto SHA-256 ficam no pacote de investigação v43–v44 entregue nesta conversa. Este commit é **documentação**, não a publicação do código executável, dos dados ou de um endpoint.
- Próximo: HMM com filtragem **causal** versus baseline por regras, mais dados futuros nunca inspecionados, auditoria de execução de setups reais; só depois calibrar Monte Carlo com operações resolvidas suficientes.
- Sem alterações a app, API, ordens simuladas ou Render; os modelos permanecem desacoplados.
