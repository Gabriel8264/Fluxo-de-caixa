# Arquitetura do projeto

## 1. Camadas

O sistema esta organizado em quatro camadas principais:

1. Entrada
   - `main.py`
   - chama `database.criar_tabela()` para compatibilidade e sobe `App()`

2. Interface
   - pasta `ui/`
   - responsavel por layout, navegacao, eventos e renderizacao

3. Servicos
   - pasta `services/`
   - centraliza regras de negocio, validacoes e orquestracao entre UI e banco

4. Persistencia
   - pasta `core/`
   - define modelos, caminhos e acesso SQLite

## 2. Fluxo de inicializacao

`main.py` executa:

1. `criar_tabela()` em `database.py`
2. `App()` em `ui/app.py`
3. `mainloop()`

`database.py` na raiz existe por legado. Para regras novas, os lugares corretos costumam ser `services/cash_service.py` e `core/database.py`.

## 3. Persistencia e arquivos locais

### 3.1 Caminhos do app

Arquivo:

- `core/app_paths.py`

Responsabilidades:

- descobrir a pasta correta em modo desenvolvimento
- descobrir a pasta correta em modo executavel
- devolver caminhos para banco, estado e recursos

### 3.2 Banco SQLite

Arquivo:

- `core/database.py`

Tabela principal:

- `movimentos`
  - `id`
  - `tipo`
  - `valor`
  - `descricao`
  - `categoria`
  - `metodo`
  - `pessoa`
  - `data`
  - `anexo`
  - `grupo_servico`
  - `papel_servico`
  - `tecnico`
  - `divisao_tecnicos`
  - `percentual_comissao_tecnico`
  - `valor_comissao_tecnico`
  - `valor_empresa`

Tabelas auxiliares:

- `categorias`
- `pessoas`
- `tecnicos`

Inicializacao importante:

- cria tabelas se nao existirem
- garante coluna `anexo`
- garante colunas do fluxo de `servico tecnico`
- completa tabelas parciais de `tecnicos` e `company_cash_adjustments`
- migra tipos legados
- migra metodos legados
- semeia categorias padrao
- sincroniza categorias e pessoas ja usadas em movimentos
- roda de forma idempotente em bancos antigos sem apagar dados

## 4. Modelos centrais

Arquivo:

- `core/models.py`

Modelos principais:

- `MovementType`
- `Movement`
- `RegistryItem`
- `CycleSummary`
- `DailyFlowSummary`

Observacao:

- `MovementType.from_db()` converte valores antigos e garante leitura consistente

## 5. Regras de negocio

Arquivo:

- `services/cash_service.py`

Pontos principais:

- iniciar novo dia
- criar, editar e excluir movimentacoes
- registrar `servico tecnico`
- listar movimentacoes com filtros
- devolver resumo geral ou do dia ativo
- devolver arvore do historico por ano, mes e dia
- devolver pacote analitico do historico
- gerenciar categorias
- gerenciar pessoas e empresas
- gerenciar tecnicos e comissoes

Metodo mais importante para o Historico:

- `get_history_scope_data(year=None, month=None, day=None)`

Ele devolve:

- `scope`
- `label`
- `start_date`
- `end_date`
- `movements`
- `summary`
- `timeline`

## 6. Sessao diaria

Arquivo:

- `services/session_service.py`

Responsabilidade:

- manter o dia ativo em `session_state.json`

Compatibilidade atual:

- recria estado padrao se o arquivo nao existir
- recria estado padrao se o arquivo estiver vazio ou com JSON invalido
- normaliza formatos antigos de data para `YYYY-MM-DD`
- preserva campos extras validos quando possivel
- nunca deve derrubar o app por erro de sessao

## 7. Interface por tela

### 7.1 Janela principal

Arquivo:

- `ui/app.py`

Responsabilidades:

- subir a janela
- montar a barra superior
- trocar entre telas
- atualizar status do dia ativo

### 7.2 Painel diario

Arquivo:

- `ui/dashboard.py`

Responsabilidades:

- mostrar panorama do dia
- mostrar ultimas movimentacoes
- mostrar analise do dia
- abrir anexos

### 7.3 Novo registro

Arquivo:

- `ui/registro.py`

Responsabilidades:

- cadastrar entrada ou saida
- cadastrar `servico tecnico`
- escolher pessoa, metodo e categoria quando aplicavel
- anexar arquivo
- calcular resumo de comissao em tempo real
- suportar um ou varios tecnicos no mesmo servico

### 7.4 Consultas e filtros

Arquivo:

- `ui/extrato.py`

Responsabilidades:

- filtrar por texto, periodo, categoria, tipo, metodo e pessoa
- mostrar extrato em tabela
- permitir ordenacao por cabecalho
- abrir anexos

### 7.5 Cadastros

Arquivo:

- `ui/cadastros.py`

Responsabilidades:

- CRUD de categorias
- CRUD de pessoas e empresas
- CRUD de tecnicos e comissoes

### 7.6 Historico

Arquivo:

- `ui/historico.py`

Responsabilidades:

- escolher recorte por ano, mes ou dia
- mostrar `Resumo`, `Analise`, `Grafico` e `Registros`
- editar e excluir registros
- abrir anexos
- exportar o periodo selecionado
- ordenar registros por clique no cabecalho

## 8. Componentes reutilizaveis

Arquivo:

- `ui/widgets.py`

Componentes importantes:

- `MarqueeLabel`
- `Card`
- `SectionFrame`
- `MetricBadge`
- `DetailMarqueeBar`
- `DateMaskEntry`
- `MoneyMaskEntry`
- `RegistryManagerFrame`
- `build_treeview_style()`

`MoneyMaskEntry` e usado nos campos de valores digitaveis. Ele aceita inteiros como reais (`100` -> `100,00`), aceita virgula ou ponto como separador decimal (`12,50` e `12.50`), remove caracteres invalidos, limita duas casas decimais e exibe o padrao brasileiro (`1.234,56`). O valor continua sendo normalizado pelos servicos para `float` antes de persistir.

## 9. Exportacoes

### 9.1 Excel

Arquivo:

- `services/excel.py`

Estado atual:

- gera `.xlsx` com Python puro
- nao depende de `openpyxl`
- recebe movimentos ja filtrados pelo periodo selecionado
- recebe metadados como tipo de exportacao, periodo, data de geracao e resumo
- hoje gera uma planilha estruturada com cabecalho institucional, resumo e tabela principal

### 9.2 PDF

Arquivo:

- `services/pdf.py`

Estado atual:

- gera `.pdf` com Python puro
- nao depende de `reportlab`
- recebe movimentos ja filtrados pelo periodo selecionado
- recebe metadados como tipo de exportacao, periodo, data de geracao e resumo
- hoje gera cabecalho institucional, resumo executivo e tabela paginada

### 9.3 Acionamento pela interface

Arquivo:

- `ui/historico.py`

Regras:

- Excel e PDF sao disparados a partir da aba `Registros`
- a exportacao deve respeitar exatamente o periodo selecionado no Historico
- o exportador nao deve depender do subconjunto visual da tabela quando o objetivo for o periodo inteiro

## 10. Servico tecnico

Documento de apoio:

- `docs/SERVICO_TECNICO.md`

Regras importantes:

- entrada bruta do servico entra como `entrada`
- comissao entra como `saida`
- valor da empresa e apenas resumo visual
- multiplos tecnicos usam soma de percentuais individuais
- a soma nao pode passar de `100%`
- servicos antigos com um tecnico continuam validos
- registros antigos sem tecnico continuam validos

## 11. Portabilidade

O projeto foi ajustado para funcionar fora do ambiente de desenvolvimento:

- `core/app_paths.py` calcula caminhos em modo normal e congelado
- `FluxoDeCaixaDiario.spec` empacota recursos
- `build_exe.ps1` automatiza o build
- o executavel gerado atualmente sai em `dist/Fluxo de caixa diario.exe` ou nome equivalente definido na `.spec`

## 12. Pontos de atencao

- a interface usa bastante `customtkinter`; mudancas grandes de layout exigem validacao visual
- o Historico e a tela mais sensivel do sistema
- textos de interface devem permanecer legiveis em portugues
- arquivos antigos `caixa.db` e `session_state.json` precisam continuar abrindo sem migracao destrutiva
- ajustes em anexos devem revisar `services/attachments.py`
- em `servico tecnico`, nunca duplicar lucro com uma segunda entrada para o valor da empresa
