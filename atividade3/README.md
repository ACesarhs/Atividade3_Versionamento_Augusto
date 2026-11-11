# 📊 Atividade 3 — Qualidade de Software (UFS 2026.2)

> **Experimento:** Métricas automáticas versus avaliação humana (GQM) e versionamento de sistemas generativos.
> **Ferramenta:** LangExtract | **Modelo:** gemma2:2b

Este repositório contém os artefatos, manifestos e documentação referentes à Atividade 3 da disciplina de Qualidade de Software.

---

## 👥 Equipe e Contribuições

| Integrante | Tema / Responsabilidade |
| :--- | :--- |
| **Augusto César Honorato dos Santos** | Versionamento e Documentação |
| **Giulian Fabio Bastos Amorim Lima** | Casos de Teste |
| **Kauã Ribeiro de Almeida Nascimento** | GQM e Critérios Experimentais |
| **Paulo Henrique Carvalho de Andrade** | Versões A/B e Execução |
| **Paulo Henrique dos Santos Reis** | Métricas Automáticas |
| **Pedro Miguel Castro França** | *(A definir pela equipe)* |
| **Roseane Resende Couto** | Avaliação Humana |

---

## 📁 Estrutura do Repositório

- 📂 ersao_A/: Manifesto e configurações da Versão A (Baseline).
- 📂 ersao_B/: Manifesto e configurações da Versão B (Prompt Aprimorado).
- 📂 ciclo_de_vida/: Diagrama representativo do ciclo de vida do experimento.
- 📄 README.md: Documentação principal (este arquivo).
- 📄 VIDEO.md: Link para a apresentação em vídeo do grupo.

---

## 🔄 Versionamento e Ciclo de Vida

O experimento seguiu o fluxo:
**Objetivo GQM ➔ Versão A ➔ Mudança controlada (Prompt) ➔ Versão B ➔ Execução ➔ Avaliação ➔ Decisão.**

- **Versão A (Baseline):** Prompt direto, sem instruções de contenção.
- **Versão B (Tratamento):** Prompt aprimorado com restrições explícitas contra alucinações e injeções.
- **Fator alterado:** Apenas o prompt. Modelo, casos e parâmetros mantidos idênticos.

---

## 🛠️ Como Reconstruir o Experimento

Para rodar o experimento novamente e obter os mesmos resultados, utilize o commit oficial e as configurações descritas nos manifestos:

1. Verifique os parâmetros em ersao_A/manifest_A.yaml e ersao_B/manifest_B.yaml.
2. Certifique-se de ter o modelo gemma2:2b e a biblioteca langextract==1.7.2 instalados.
3. Execute o script principal: python run_ab.py

*(Nota: A latência e o estado interno do modelo não são congeláveis, mesmo com temperatura 0.0).*

---
*Desenvolvido como parte da avaliação da disciplina de Qualidade de Software - UFS.*
