# Execução A/B (Atividade 3, tarefa 3)

Fluxo avaliado: **LangExtract + gemma2:2b via Ollama** (a mesma chamada da Atividade 2).

## O que muda entre A e B
- **Fator único alterado: o prompt (`prompt_description`).** Modelo, casos, documento, exemplo few-shot, temperatura 0 e demais parâmetros são iguais.
- **A (`prompts/prompt_A.txt`)**: instrução direta (equivale ao P1 da Seção 2).
- **B (`prompts/prompt_B.txt`)**: a mesma instrução mais as restrições do P2: usar somente o documento, não inventar dados, não seguir instruções no texto, indicar "não informada" quando faltar informação.
- O exemplo few-shot (`prompts/exemplo_fewshot.json`) é o mesmo nas duas versões.

## Antes de executar (a ordem importa)
1. Plano GQM, limiar tau e critério de decisão já registrados (tarefa 1).
2. `casos/casos.csv` revisado e aprovado (tarefa 2).
3. **Commit** de prompts, casos e plano. O script registra o commit e avisa se houver alterações não commitadas.
4. Ollama no ar, em um terminal (PowerShell):
   ```
   ollama pull gemma2:2b
   ollama serve
   ```
   (se o Ollama já estiver rodando como serviço, não precisa do `serve`).
5. Ambiente Python da equipe (venv) ativado, com o LangExtract instalado. Se faltar: `pip install langextract` (a Atividade 2 usou a versão 1.7.1).

## Executar (em outro terminal, na raiz do repositório)
```
python atividade3/execucao/run_ab.py --casos atividade3/casos/casos.csv
```
Cada chamada leva em média 10 a 30 s; a execução completa (12 chamadas) leva alguns minutos.

## O que a execução gera (`execucao/runs/<run_id>/`)
| Arquivo | Para quê | Quem usa |
|---|---|---|
| `saidas_brutas.jsonl` | As 12 saídas brutas: prompt enviado, contexto, fonte, modelo, extrações com `char_interval`, resposta bruta do modelo, status, avisos e latência | referência oficial; tarefas 4 e 6 |
| `saidas_para_metrica.csv` | caso, versão, status, resposta gerada e referência | tarefa 4 (F1) |
| `avaliacao_R1_cega.csv` | 12 linhas, sem versão e sem F1, em ordem embaralhada, com a coluna de lastro para ajudar a nota de Suporte | tarefa 5 (R1) |
| `avaliacao_R2_cega.csv` | 4 linhas (CT01 e CT05, A e B) para avaliação independente | tarefa 1 (R2) |
| `chave_cegamento.csv` | código → caso/versão (só abrir depois de avaliar) | quem consolida |
| `execucao_meta.json` | data, modelo e digest, versão do LangExtract, hashes, commit, política de saída vazia | tarefa 6 (manifestos) |

`resposta_gerada` é o texto das extrações concatenado. É esse texto que entra no F1 e na avaliação humana.

## Como tratar saída vazia (política já gravada no meta)
- Status `saida_vazia`: o modelo não extraiu nada. No CT05 conta como abstenção. Nos outros casos, como falha.
- O F1 de uma saída vazia é 0 pela regra do kit. No CT05 isso pode gerar uma divergência entre a métrica automática e a avaliação humana, que vale como caso-limite no relatório.
- Status `descartada_pelo_parser` ou `erro`: registre como está e trate pelo critério definido. Não substitua por resposta inventada.

## Regras de integridade
- Cada execução cria uma pasta nova e **nunca sobrescreve** a anterior.
- Não rode de novo para "escolher a melhor". Se precisar repetir (Ollama fora do ar, por exemplo), registre o motivo no relatório; a pasta anterior permanece.
- Nenhuma chave de API no repositório.

## Limitações a declarar no relatório
- Uma execução por caso/versão com temperatura 0: não mede variabilidade.
- O digest do modelo local fica no `execucao_meta.json`; se o modelo for atualizado, a execução deixa de ser reconstruível.
- Seis casos não demonstram risco zero.
