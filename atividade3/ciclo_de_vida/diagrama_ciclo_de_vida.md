# Diagrama do Ciclo de Vida

`mermaid
flowchart LR
    A[Objetivo GQM] --> B[Versao A - prompt baseline]
    B --> C[Mudanca controlada - prompt com restricoes]
    C --> D[Versao B - prompt aprimorado]
    B --> E[Execucao - 6 casos x 2 versoes]
    D --> E
    E --> F[12 saidas brutas]
    F --> G[Metrica automatica - F1 lexical]
    F --> H[Avaliacao humana - R1 e R2]
    G --> I[Tabela e grafico]
    H --> I
    I --> J[Decisao experimental]
    J --> K[Acompanhamento]
    J --> L[Manifestos A e B preservados]
