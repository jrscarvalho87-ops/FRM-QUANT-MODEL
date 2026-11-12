# RFM Quant — Entrega unificada de investigação (v48)

**Estado em 12/13 novembro 2026: research MVP — NÃO validado para negociação real.**

## Auditoria reproduzida

A entrega ZIP da conversa inclui um painel offline `INICIO_AQUI.html`, seis arquivos técnicos originais (v41, v42, v43–44, v45, v46 e v47), relatórios, CSVs e script de execução automática dos testes.

| Módulo | Testes executados nesta auditoria |
| --- | ---: |
| v41 volatilidade | 6 / 6 |
| v42 horizontes | 8 / 8 |
| v43–44 tendência/direção | 15 / 15 |
| v45 HMM | 18 / 18 |
| v46 feature store | 20 / 20 |
| v47 auditoria execução/sweeps | 22 / 22 |
| **Total** | **89 / 89** |

**Correção de empacotamento:** a v42 isolada falha um teste por precisar de `../RFM_Quant_Modelos_v41/comparacao_modelos_v41.csv`; o pacote unificado extrai as duas versões como pastas irmãs e passa os oito testes de v42. Não se trata de erro na métrica, mas de dependência documental/técnica que deverá ser eliminada antes de um release final do modelo.

## O que efetivamente foi medido

- 140.160 candles de 15 minutos (BTC, ETH, SOL e ZEC; novembro 2025–outubro 2026).
- Protótipo original v38: 233 candidatos, 14 elegíveis, **2** TP/SL resolvidos; +0,801711R líquido diagnóstico.
- Política alternativa **sem expiração de contexto**: 6 TP/SL (2 TP, 4 SL), −0,384518R.
- Hipótese adicional de Asian High/Low 00–08 UTC **NÃO confirmada**: 8 saídas (2 TP, 5 SL, 1 BE), −1,707851R.
- 219 candidatos filtrados por liquidez (202 sem sweep nomeado na janela de 4h, 17 invalidados).
- Modelos de mercado testados; **NÃO existe classificador validado de win rate RFM**, nem edge confirmado.
- Monte Carlo no pacote é **exclusivamente hipotético**: probabilidades e payouts fixados pelo analista para ilustrar incerteza, não calibrados a trades da RFM.

## Estado do produto

O serviço Render `https://rfm-quant.onrender.com` tem o último deploy observado como `live`, mas não inclui modelos v41–v47. O código de investigação está apenas nos arquivos ZIP locais; esta branch contém **documentação**, não as implementações executáveis. Não efetuar merge nem deployment automático sem revisão técnica.

## Bloqueios para um sistema fiel e validado

1. Confirmar definições de sweep, Asian High/Low, Fib 67%/75%, stop estrutural e BE +1R.
2. Corrigir discrepâncias do protótipo, incluindo expiração de ordens por mudança de contexto e limiar de reversão de 2%.
3. Resolver candles ambíguas com menor timeframe quando possível.
4. Obter e verificar os meses de 2024-11 a 2025-10; estes não puderam ser descarregados no ambiente sem acesso de rede.
5. Pré-especificar as regras e testá-las em dados realmente inéditos; obter amostra muito maior de operações independentes e fechadas.
6. Só depois estudar Monte Carlo empírico, custos reais e eventual integração read-only na aplicação.

**Entrega fechada como MVP de investigação; NÃO fechada como estratégia rentável.** Evitar treinar modelos para forçar 60–70% win rate in-sample.

*Integridade:* os seis arquivos têm hashes SHA-256 guardados no pacote, e o ZIP unificado foi verificado por CRC após criação.
