# RFM Quant — auditoria histórica de 30 000 velas (2026-11-10)

> **Experiência quantitativa, NÃO validação da RFM discricionária.** A estratégia do utilizador tem Fibonacci 67–75%, FVG ativo na Gold Zone e liquidez **relevante na estrutura** como essenciais; BOS, sweep e POC não são requisitos universais. A proteção confirmada é mover SL para o preço de entrada aos +1R.

## Proveniência
- Fonte: velas OHLCV confirmadas da API pública OKX, paginadas por RFM Quant, sem credenciais de exchange.
- Mercados: BTC-USDT-SWAP, ETH-USDT-SWAP e SOL-USDT-SWAP.
- Amostra: 10 000 velas de 15m por instrumento; 2026-07-29 16:30 UTC a 2026-11-10 20:15 UTC.
- [Execução completa e ficheiros CSV/JSON](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/actions/runs/42896421388).
- Regras mecanizadas **provisórias**: pivôs confirmados com janela de 3 velas para âncoras, sinal emitido apenas após confirmação do extremo e sem primeiro toque retroativo na Gold Zone; FVG de três velas ainda ativo na zona. O gerador **impulse_no_bos** não exige BOS.
- Características de liquidez (EQH/EQL, BSL/SSL, máximos e mínimos de períodos anteriores) foram medidas, **mas a relevância mínima não foi convertida em filtro obrigatório**: por isso o modelo não corresponde integralmente à RFM. Não se adotou nenhuma regra de vídeos.
- POC OHLCV apenas aproximado e opcional; a anotação do contexto 4H foi acrescentada ao código após esta execução, não afeta os números deste snapshot.
- Execução: limite no Fibonacci 75%, validade 8 velas, stop no 100%, take-profit no 0%, risco de referência 1% do capital fictício de 10 000 USDT por mercado, nocional máximo 1x, taxa 5 bps/lado, slippage 2 bps/lado, saída stop-first em barras ambíguas. Sem funding/liquidações/spread variável ou impacto de mercado.
- BE aos +1R: SL passa à entrada **a partir da vela seguinte** ao gatilho, pela ambiguidade intravela OHLC. BE bruto pode dar resultado líquido negativo.

## Gerador sem BOS obrigatório: BE vs. sem BE

| Métrica | BTC | ETH | SOL |
|---|---:|---:|---:|
| Sinais gerados | 310 | 334 | 333 |
| Trades fechados com BE | 80 | 82 | 90 |
| Saídas por BE | 39 | 39 | 39 |
| Média líquida R com BE | -0,1372R | -0,0754R | -0,1293R |
| Retorno simulado com BE | -10,4401% | -6,0838% | -11,1068% |
| Trades fechados sem BE | 79 | 74 | 85 |
| Média líquida R sem BE | -0,1135R | +0,0487R | -0,0251R |
| Retorno simulado sem BE | -8,6589% | +3,4545% | -2,3624% |

**A experiência foi negativa com BE nos três mercados.** O BE não melhorou a rentabilidade nesta amostra; não implica que prejudique a RFM real. Como saídas diferentes mudam a possibilidade de entrada posterior, as comparações de carteira não equivalem a pares independentes de trades.

## Comparação secundária: hipótese com BOS obrigatório

| Métrica com BE | BTC | ETH | SOL |
|---|---:|---:|---:|
| Sinais | 29 | 40 | 28 |
| Trades fechados | 5 | 6 | 9 |
| R médio líquido | +0,0344R | +0,0477R | +0,0947R |
| Retorno fictício | +0,1703% | +0,2740% | +0,8435% |

**Amostra muito pequena** e resultado não generalizável. Não usar esta comparação para impor BOS obrigatório.

## Machine Learning: 252 operações combinadas, quatro folds cronológicos

Foram concatenados os datasets de trades fechados BTC/ETH/SOL, ordenados pelo instante do sinal. Cada treino exclui trades cuja saída ocorre depois do início do teste (purging). O modelo conhece o ativo através de indicadores fixos, não resultados futuros. Quatro conjuntos de teste com 25 operações cada, comparando previsão constante do treino, XGBoost e regressão logística. As probabilidades foram avaliadas pelo Brier Score (menor é melhor).

| Indicador, média dos quatro folds | Brier |
|---|---:|
| Previsão constante (baseline) | **0,162347** |
| XGBoost | 0,182615 |
| Regressão logística | 0,190612 |

**Nenhum ML superou o baseline.** Não provar edge, nem adicionar um filtro automático de IA. A investigação já analisou a amostra, que deixa de constituir holdout final intacto. As oportunidades e trades dos três ativos são parcialmente correlacionados.

## Diagnóstico da liquidez e confluências

Dos 252 trades executados do modelo sem BOS, 191 tiveram a marcação experimental de quebra contextual por fecho de vela e 61 não. A média R foi negativa em ambos os grupos; portanto, isto **não demonstra** que a marcação de BOS tenha valor preditivo. Apenas **6 dos 252** tinham o POC OHLCV aproximado na Gold Zone, insuficiente para conclusões. A contagem bruta de níveis de liquidez esteve entre 2 e 69 por trade e pode incluir níveis sem importância prática.

Por isso, um próximo passo essencial é distinguir níveis estruturais antigos, testados/atravessados e relevantes para o swing, usando **definições observáveis fixadas antes dos testes**, sem exigir que a liquidez esteja perto da Gold Zone ou do TP. O novo código regista adicionalmente se um nível já foi ultrapassado depois de confirmado, mas uma ultrapassagem **não equivale a liquidity sweep** e não deve impor um filtro por si só.

## Desenvolvimento de código e próximos critérios

- [Gerador de pivôs sem BOS](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/rfm_impulse_candidates.py).
- [Execução com BE 1R ou sem BE](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/execution.py).
- [Liquidez estrutural causal](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/structural_liquidity.py).
- [Contexto 4H com velas completas, informativo](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/htf_context.py).
- [Walk-forward com XGBoost, logística e baseline](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/research/quant_pipeline.py).
- [Análise combinada reproduzível](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/research/pooled_walk_forward.py).
- [Block bootstrap com amostra mínima de 30 trades](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/blob/main/research/robustness.py).

**Portas de validação para um teste fiel:** anotar exemplos reais de âncoras Fibonacci e liquidez estrutural aceite/rejeitada; congelar definição de relevância, mitigação do FVG e validade das ordens; comparar setups com/sem BOS e o BE em períodos novos cronologicamente intactos; verificar custos, funding, spreads e informação temporal; só depois analisar se ML acrescenta vantagem. Não existe aqui qualquer recomendação de operar futures com dinheiro real.
