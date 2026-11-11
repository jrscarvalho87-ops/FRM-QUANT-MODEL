# RFM Quant — Range, Fibonacci, Anotações e Modelos (11-11-2026)

## Regras humanas que não devem ser alteradas

Fibonacci **em uptrend: high → low; em downtrend: low → high**, sempre em **extremos dos pavios**, não em corpos. Isto descreve a ordem de desenho da ferramenta, não a ordem cronológica da formação do movimento. Em long o 0% fica no topo e o 100% em baixo; em short o inverso. Gold Zone 67–75%, FVG ativa sobreposta e liquidez estrutural relevante são essenciais. BOS, sweep e POC são opcionais; 4H premium/discount é informação. TP próximo de 0%, SL próximo de 100%, BE aos +1R.

Os quatro exemplos cegos demonstraram que **um low/high geométrico não implica um swing estrutural válido** e que o utilizador procura ranges e estrutura concreta em vez de expansions isoladas. Ainda não existe limiar humano aprovado de range, número de pivôs, volume ou volatilidade.

## Casos revistos e observações causais

As quatro classificações humanas foram usadas APENAS para especificar as variáveis de investigação, sem treinar um classificador de setups nem ajustar thresholds com base em lucros.

| Exemplo | Decisão | Peak high-low / ATR prévio | Percentil no ativo | Volume da vela / média das 20 anteriores |
|---|---|---:|---:|---:|
| SOL 25-08-2026, long | Rejeitado por expansão brusca | 5,99 | 94.º | 0,84 |
| BTC 16-10-2026, long | Rejeitado por volume/PA e low inadequados | 3,85 | 76.º | 2,57 |
| SOL 30-10-2026, long | Incerto, Fib inferior/PA fraca | 1,31 | 16.º | 0,49 |
| SOL 03-08-2026, short | Aceite com reservas sobre estrutura | 2,95 | 68.º | 0,74 |

A tabela mede máximo **high-low / ATR prévio** e não necessariamente o **true-range/ATR** do motor, se houver gaps. As medidas só usam velas até ao sinal. O rácio 2,57x na vela BTC rejeitada mostra que **volume pontual elevado não corresponde automaticamente a volume/price action de qualidade**. Quatro casos não justificam filtros.

## Implementações e testes

- **market_structure_context.py**: medidas causais da amplitude/eficiência antes do swing, eficiência e concentração da expansão durante o swing, true range relativo ao ATR prévio, pivôs confirmados e volume relativo. Nenhum valor se torna automaticamente filtro.
- **rfm_impulse_candidates.py**: acrescenta esses descritores aos candidatos com âncoras de pavio e FVG ativa; BOS continua não obrigatório. Não afirma identificar ranges humanos com fidelidade.
- **fibonacci.py**: a direção de desenho é explícita e testada separadamente da aritmética de níveis.
- **research/quant_pipeline.py**: inclui as variáveis novas como contexto exploratório.
- **research/model_ablation.py**: protocolo pré-definido de três conjuntos de features: preço, preço + estrutura e preço + estrutura + liquidez. Compara baseline de probabilidade constante, regressão logística regularizada e XGBoost. Usa os mesmos blocos de timestamps UTC para todos, exclui do treino qualquer trade com saída ainda desconhecida na primeira decisão de teste, aplica embargo de 15 minutos e calcula imputações só a partir do treino.
- **research/compare_models_frozen.py**: agrupa BTC, ETH e SOL do mesmo histórico corrigido e executa o protocolo de ablação. Brier Score/log-loss medem previsões de resultado positivo nos trades simulados já fechados, NÃO retorno de carteira. O CSV com as quatro avaliações humanas NÃO entra no treino nem no alvo.
- **GitHub CI**: testes unitários, checks de no-lookahead, geometria e regressão long/short, splitting temporal, validação de dados, e replay histórico com histórico OHLCV fixo e checksum.



## Resultado efetivo da experiência quantitativa congelada

Reexecutado o snapshot público da OKX com **30.000 velas confirmadas 15m** e checksum histórico igual ao anterior. Foram produzidos **893 candidatos com Fib geometricamente válida**, dos quais **236 trades simulados fechados com a regra BE aos +1R** (75 BTC, 79 ETH, 82 SOL). Estes dados continuam a ser um **proxy experimental, não a RFM validada**.

A comparação reuniu esses 236 trades em **4 folds temporais de 25 timestamps de sinal cada**, iguais para todos os modelos, com embargo de 15 minutos e exclusão de operações de treino cujo fecho não fosse conhecido à data de teste. Os grupos de features são predefinidos no código, não foram otimizados em função das quatro correções humanas.

| Conjunto de features | Brier: XGBoost | Brier: regressão logística |
|---|---:|---:|
| Apenas preço | 0,165587 | 0,161453 |
| Preço + estrutura/range/volume | 0,159294 | 0,167288 |
| Preço + estrutura + liquidez | 0,160386 | 0,178067 |
| **Baseline constante (sem features)** | **0,149548** | **0,149548** |

A baseline também teve a melhor **log-loss: 0,478173**; a melhor combinação com XGBoost (estrutura) teve log-loss 0,526210. **Nenhum modelo supera a baseline constante**. O XGBoost com estrutura melhorou sobre o XGBoost só com preço, mas não prova edge.

Estes números referem-se a **classificação probabilística de R positivo**, não à rentabilidade de uma carteira; o treino está condicionado aos trades simulados executados/fechados, com viés de seleção e ativos correlacionados. A amostra histórica já foi examinada; não existe holdout final intocado. Não usar estes modelos para dar sinais reais nem alterar a estratégia para maximizar estes scores retrospectivos.

Reprodução e CSV completos: [GitHub Action 42932357777](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/actions/runs/42932357777), artefacto com ficheiro model_ablation.json e todos os eventos/trades.

## Limitações / próxima validação

O gerador continua a ser proxy mecânico de pivôs; não reproduz a seleção humana do low/high válido. Os sinais BTC/ETH/SOL podem estar correlacionados; a simulação por ativo não é uma carteira agregada. A janela histórica de 30 mil velas já foi vista, logo folds nela são APENAS diagnóstico retrospectivo, sem holdout final independente. A decisão humana de que é bom range precisa de ser traduzida em critérios claros a partir de novos exemplos cujo resultado futuro esteja oculto, antes de usar novos dados futuros para validar edge. Funding, slippage real, liquidez de livro, impacto e caminho intravela de BE ainda são limitações.

**Isto é investigação e backtesting, não execução de futuros reais.**
