# Fluxo de caixa diario

Aplicacao desktop em Python com `customtkinter` para operacao diaria de fluxo de caixa, com cadastro de movimentacoes, filtros, historico analitico, anexos e exportacao para Excel e PDF sem dependencias externas para exportacao.

## Objetivo

Este repositorio foi organizado para facilitar manutencao, refinamentos visuais e empacotamento em `.exe` para uso em qualquer PC Windows.

## Visao geral rapida

- Entrada principal: `main.py`
- Janela principal e navegacao: `ui/app.py`
- Regras de negocio: `services/cash_service.py`
- Persistencia SQLite: `core/database.py`
- Modelos centrais: `core/models.py`
- Aba de historico: `ui/historico.py`
- Exportacao Excel: `services/excel.py`
- Exportacao PDF: `services/pdf.py`
- Arquivos portateis do app: `core/app_paths.py`

## Funcionalidades principais

- Painel diario com resumo, ultimas movimentacoes e analise financeira
- Novo registro com anexo, mascara de data e selecao de categoria e pessoa
- Consultas e filtros com extrato e abertura de anexos
- Cadastros de categorias e pessoas/empresas
- Historico por ano, mes e dia com resumo, entradas e saidas, analise, graficos e registros
- Edicao e exclusao de registros no historico
- Exportacao do periodo selecionado para Excel e PDF
- Execucao portatil com banco e estado gravados ao lado do executavel

## Estrutura do projeto

```text
PythonProject1/
|-- assets/
|   `-- fluxo_caixa.ico
|-- core/
|   |-- app_paths.py
|   |-- database.py
|   `-- models.py
|-- services/
|   |-- attachments.py
|   |-- cash_service.py
|   |-- excel.py
|   |-- pdf.py
|   `-- session_service.py
|-- ui/
|   |-- app.py
|   |-- cadastros.py
|   |-- dashboard.py
|   |-- extrato.py
|   |-- historico.py
|   |-- registro.py
|   |-- theme.py
|   `-- widgets.py
|-- build_exe.ps1
|-- FluxoDeCaixaDiario.spec
|-- main.py
`-- database.py
```

## Como executar em desenvolvimento

```powershell
.\.venv\Scripts\python.exe main.py
```

## Como gerar o executavel

```powershell
.\build_exe.ps1
```

Saida esperada:

- `dist\Fluxo de caixa diario.exe`

## Documentacao detalhada

- Arquitetura e fluxo interno: `docs/ARQUITETURA.md`
- Guia de manutencao rapida: `docs/GUIA_DE_MANUTENCAO.md`
- Estrutura completa da aba Historico: `docs/HISTORICO.md`
- Gabarito operacional de trabalho: `docs/GABARITO_OPERACIONAL.md`

## Observacoes importantes

- `database.py` na raiz existe por compatibilidade com a interface antiga. Novas regras devem ir para `services/cash_service.py` e `core/database.py`.
- As exportacoes de Excel e PDF foram implementadas sem depender de bibliotecas externas de exportacao.
- O app foi preparado para rodar em modo portatil: banco SQLite e `session_state.json` ficam ao lado do executavel.
- Sempre que houver alteracao visual importante, vale validar especialmente `ui/app.py`, `ui/historico.py`, `ui/dashboard.py` e `ui/registro.py`.
- A rolagem do Historico foi centralizada em um unico scroll principal baseado em `Canvas`; a tabela de registros mantem scroll proprio apenas para a grade.
