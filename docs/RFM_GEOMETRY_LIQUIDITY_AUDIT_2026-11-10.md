# RFM Quant — Auditoria de âncoras Fibonacci e contexto estrutural (2026-11-10)

## Âmbito
A RFM confirmada exige Fibonacci 67–75%, FVG na Gold Zone e liquidez estrutural relevante para o movimento. BOS, POC e sweep são opcionais. O stop passa para break-even aos +1R. Nenhuma regra foi acrescentada com base em vídeos.

Os módulos quantitativos continuam a ser hipóteses de investigação; não substituem a escolha discricionária de âncoras nem a avaliação humana da relevância da liquidez.

## Auditoria do gerador sem BOS anterior
Os 977 sinais gerados sobre dados OHLCV reais da OKX (10 000 velas 15m por ativo) foram revistos quanto à geometria das âncoras:

| Mercado | Sinais | Âncoras inconsistentes | Percentagem |
|---|---:|---:|---:|
| BTC-USDT-SWAP | 310 | 19 | 6,13% |
| ETH-USDT-SWAP | 334 | 33 | 9,88% |
| SOL-USDT-SWAP | 333 | 32 | 9,61% |
| Total | 977 | 84 | 8,60% |

**16 de 252 trades fechados** no histórico anterior correspondiam a sinais com âncoras inconsistentes. Um 0% ou 100% mal selecionado distorce a Gold Zone, o risco e os alvos. Retirar os sinais da tabela, sem reexecutar o simulador, não equivale a um novo backtest.

## Correção de geometria
O novo módulo **swing_geometry.py** verifica, sem olhar para velas futuras, que:
- Em posições long, o 100% é o mínimo e o 0% é o máximo no intervalo temporal entre âncoras.
- Em posições short, o 100% é o máximo e o 0% é o mínimo no mesmo intervalo.
- Regista duração do movimento e atraso de confirmação de pivô.

O gerador experimental **rfm_impulse_candidates.py** rejeita pares de âncoras inconsistentes antes de procurar entrada; mantém o BOS opcional. A geometria consistente é uma condição necessária à interpretação das duas âncoras como extremos do movimento, **não é prova de que seriam as âncoras que o utilizador escolheria**.

## Liquidez estrutural mensurada — não é filtro
O novo módulo **swing_liquidity_context.py** separa níveis previamente conhecidos que:
- estão dentro da amplitude de preços do movimento;
- se formaram entre as âncoras;
- já eram conhecidos antes do movimento;
- ainda não foram ultrapassados depois de confirmados;
- representam tipos distintos como BSL/SSL, EQH/EQL e máximos/mínimos prévios.

**Não exige proximidade à Gold Zone ou ao take-profit. Não impõe um score arbitrário nem número mínimo de zonas.** Um nível ultrapassado não implica necessariamente um liquidity sweep, e a presença de um nível não mede ordens reais disponíveis.

## Histórico fixo e reprodução
- Fonte: [snapshot público OKX utilizado anteriormente](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/actions/runs/42898175611).
- Janela exata: **29-07-2026 16:45 UTC a 10-11-2026 20:30 UTC**, 10 000 velas por ativo.
- A exportação histórica suporta agora um timestamp final fixo, sem misturar históricos de períodos diferentes.
- **research/audit_geometry_snapshot.py** verifica o SHA-256 de preços e volumes contra o snapshot anterior; se houver alteração, recusa comparações antes/depois.
- Reexecuta custos, stops, TP e a regra confirmada BE aos +1R; compara separadamente a variante sem BE apenas como controlo.
- Os dados anteriores já foram examinados, portanto um resultado melhor nesta janela **não seria validação independente fora da amostra**.


## Reexecução verificada sobre as mesmas 30 000 velas
O processo de auditoria concluiu com assinaturas SHA-256 idênticas às do snapshot anterior, pelo que os preços e volumes comparados são os mesmos.

| Mercado | Sinais antigos | Novos sinais com âncoras geométricas válidas | Trades concluídos com BE | Retorno simulado anterior | Retorno após correção |
|---|---:|---:|---:|---:|---:|
| BTC | 310 | 291 | 75 | -10,4401% | -9,9347% |
| ETH | 334 | 301 | 79 | -6,0838% | -6,4282% |
| SOL | 333 | 301 | 82 | -11,1068% | -9,3069% |

Os novos sinais correspondem exatamente à eliminação dos 84 candidatos anteriormente identificados como inconsistentes. Continuam a existir perdas líquidas nos três mercados. **São resultados de uma hipótese mecânica, não uma validação do edge da RFM real.** As saídas BE e a exposição nocional usam os pressupostos já documentados.

## Problema quantitativo adicional: liquidez que aparece sempre
A primeira métrica de liquidez contextual positiva dava **893/893 setups (100%)**. Ao inspecionar a distribuição, o número mínimo de níveis considerados era sempre **dois**: as próprias âncoras alta/baixa da Fibonacci, que eram automaticamente identificadas como pivôs de estrutura.

Isso não constitui uma confluência adicional; é um artefacto da definição. **Foi por isso introduzida uma contagem separada de liquidez estrutural independente das duas velas-âncora**, baseada em níveis conhecidos e ainda não ultrapassados. A contagem antiga é mantida apenas para diagnóstico de comparabilidade, não para decisões de entrada.

A nova métrica continua a ser uma hipótese explicativa — **não** foi convertida num filtro com limiar ou distância obrigatória à Gold Zone/TP. A sua distribuição e utilidade precisam de validação com setups anotados e novas janelas fora da amostra.

## Testes e bloqueios restantes
Testes de longa/curta, consistência de máximos e mínimos, rejeição de futuros, períodos completos, dados com falhas, sincronização de candles e gestão BE estão no [GitHub Actions](https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/actions).

Não está demonstrada qualquer vantagem estatística da RFM original. Falta validar as âncoras e a relevância da liquidez com exemplos históricos anotados, fixar regras antes de testes futuros, reservar períodos não analisados e modelar custos reais, funding e execução intravela.
