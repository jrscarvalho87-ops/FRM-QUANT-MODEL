# RFM Quant — Protocolo de revisão cega de setups (2026-11-10)

## Finalidade
Distinguir decisões humanas da RFM (seleção do swing da Fibonacci, FVG ativa e relevância das zonas de liquidez) das hipóteses mecânicas usadas nos backtests experimentais. **A estratégia não é alterada por esta amostra** e não são importadas regras de vídeos ou otimizações por resultados observados.

## Amostra histórica
36 casos, **12 por BTC-USDT-SWAP, ETH-USDT-SWAP e SOL-USDT-SWAP**, extraídos das mesmas 30 000 velas 15m confirmadas da OKX do estudo anterior. O pack offline tem gráficos de velas **até ao fecho do sinal, sem velas seguintes, resultado da operação, PnL ou motivo de saída**.

- Seleção com semente 20261110 e quotas predefinidas para tipos de contexto estrutural; sem utilizar retornos, taxas de acerto, saídas ou performance futura.
- Distribuição: 19 casos com níveis exteriores em ambos os lados, 7 exteriores unilaterais, 8 com nível independente ainda não ultrapassado dentro do swing e 2 sem nível exterior.
- Esta é uma **amostra deliberadamente estratificada**, não representativa da frequência natural de setups. Não utilizar a percentagem de aprovação como estimativa da taxa de setups reais.
- Fonte dos sinais: auditoria de âncoras geometricamente válidas, sem BOS como requisito, exigindo a FVG ativa a sobrepor-se à Gold Zone 67–75%.
- **Resultado exploratório anterior:** no próprio conjunto de 893 sinais válidos, apenas 22 tinham nível estrutural independente ainda não ultrapassado dentro da amplitude do swing. Por outro lado, zonas exteriores estavam quase sempre presentes. Isto evidencia que uma contagem de linhas não basta para definir relevância.

## Ficheiros gerados e verificações
- **RFM_Quant_Revisao_Cega_36_Setups.html** — aplicação autónoma que não usa Internet; mostra velas históricas, Gold Zone, FVG ainda ativa e amostras de níveis estruturais conhecidos no instante do sinal.
- **RFM_Quant_Revisao_Cega_36_Setups.json** — manifesto auditável de casos e estratos selecionados.
- **build_review_pack.py** — script Python de construção reproduzível, a partir dos ZIP históricos do projeto (disponibilizado juntamente com o pack).
- O HTML foi validado num navegador Chromium: navegação, rádio, notas, exportação CSV/JSON, sem erros de JavaScript. A categoria/estrato calculado pelo algoritmo permanece oculta durante a avaliação para reduzir enviesamento humano.
- Testes Python locais: 4 aprovados; confirmam 36 IDs únicos, 12 por ativo, geração determinística, FVG causal sobreposta e ausência de dados de performance futura.
- SHA-256 do HTML: `97a6301bf7e6c493abd1731d79cacc5b093d8cceafa4f09523eef0b57d062def`
- SHA-256 do manifesto JSON: `0bf7e51b65fe7edb9a4ab9587c20172c98793a8441db8e40948a8ef40651887f`

## Como usar
Abrir o HTML localmente. Para cada um dos 36 casos, responder às quatro perguntas com **sim, não ou incerto**: (1) âncoras Fibonacci corretas; (2) liquidez estrutural relevante; (3) FVG válida e sobreposta à Gold Zone; (4) aceitarias o setup da RFM. Acrescentar notas quando uma âncora, liquidez ou FVG deva ser rejeitada. O pack guarda o progresso no navegador quando permitido, e permite **exportar CSV ou JSON** para continuar noutro computador.

O validador no GitHub, **research/annotation_review.py**, recebe o CSV exportado e o manifesto JSON:

```bash
python -m research.annotation_review     --manifest RFM_Quant_Revisao_Cega_36_Setups.json     --labels RFM_Quant_Labels_36_Casos.csv     --output RFM_Quant_Relatorio_Anotacoes.json
```

O validador rejeita IDs duplicados/desconhecidos, timestamps ou direções adulterados, valores não reconhecidos e campos de resultados futuros infiltrados no manifesto. Produz contagens de aceitação e desacordos da classificação humana com os indicadores mecânicos, **não um novo backtest**.

## Depois da revisão
1. Auditar padrões das justificações humanas (âncoras erradas, zonas de liquidez sem relevância, FVG mitigadas etc.).
2. Traduzir critérios **claros e reproduzíveis** para uma regra de pesquisa congelada e validada com exemplos em que o resultado futuro continue oculto.
3. Reavaliar exclusivamente em períodos posteriores **não utilizados nesta investigação**, incluindo taxas, slippage e BE aos +1R.
4. Só usar XGBoost se ganhar face ao baseline em avaliação temporal purgada e num holdout intocado; os experimentos anteriores **não** demonstraram edge.

**Investigação histórica e simulação exclusivamente; não efetua trading real de futuros.**
