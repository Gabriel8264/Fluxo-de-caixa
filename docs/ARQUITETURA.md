# Arquitetura do projeto

## 1. Camadas

O sistema esta organizado em quatro camadas principais:

1. Entrada
   - `main.py`
   - chama `database.criar_tabela()` para compatibilidade e depois sobe `App()`

2. Interface
   - pasta `ui/`
   - responsavel por layout, navegacao, eventos de tela e renderizacao visual

3. Servicos
   - pasta `services/`
   - centraliza regras de negocio, validacoes e orquestracao entre UI e banco

4. Persistencia
   - pasta `core/`
   - define modelos, caminho de arquivos e acesso SQLite

## 2. Fluxo de inicializacao

### 2.1 Entrada

`main.py` executa:

1. `criar_tabela()` em `database.py`
2. `App()` em `ui/app.py`
3. `mainloop()`

### 2.2 Compatibilidade

`database.py` na raiz e uma camada de compatibilidade. Ele reaproveita `CashService`, mas existe para manter o ponto de entrada antigo funcionando. Nao e o lugar ideal para novas regras.

## 3. Persistencia e arquivos locais

### 3.1 Caminhos do app

Arquivo: `core/app_paths.py`

Responsabilidades:

- descobrir a pasta correta em modo desenvolvimento
- descobrir a pasta correta em modo executavel
- devolver caminhos para dados persistentes
- devolver caminhos para recursos como icone

### 3.2 Banco SQLite

Arquivo: `core/database.py`

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
- garante colunas do fluxo de `serviço técnico`
- migra tipos legados como `pagar` e `receber`
- migra metodos legados como `debito` e `credito`
- semeia categorias padrao
- sincroniza categorias e pessoas ja usadas em movimentos

## 4. Modelos centrais

Arquivo: `core/models.py`

Modelos principais:

- `MovementType`
- `Movement`
- `RegistryItem`
- `CycleSummary`
- `DailyFlowSummary`

Observacao:

- `MovementType.from_db()` converte valores antigos e garante leitura consistente

## 5. Regras de negocio

Arquivo: `services/cash_service.py`

Pontos principais:

- inicializar repositorio e sessao
- iniciar novo dia
- criar, editar e excluir movimentacoes
- registrar `serviço técnico` como fluxo financeiro especializado
- listar movimentacoes com filtros
- devolver resumo geral ou do dia ativo
- devolver arvore do historico por ano/mes/dia
- devolver pacote analitico do historico para a UI
- gerenciar categorias
- gerenciar pessoas/empresas
- gerenciar tecnicos e comissoes

Regras importantes do `serviço técnico`:

- o valor bruto do servico entra como `entrada`
- a comissao dos tecnicos sai como `saida`
- o valor da empresa e apenas resumo visual e nao gera nova movimentacao
- com multiplos tecnicos, a comissao total e a soma dos percentuais individuais
- a soma dos percentuais nao pode ultrapassar `100%`
- servicos antigos com um tecnico continuam validos
- registros antigos sem tecnico continuam validos

Documento de apoio:

- `docs/SERVICO_TECNICO.md`

O metodo mais importante para telas de historico e:

- `get_history_scope_data(year=None, month=None, day=None)`

Ele devolve um pacote com:

- `scope`
- `label`
- `start_date`
- `end_date`
- `movements`
- `summary`
- `timeline`

## 6. Sessao diaria

Arquivo: `services/session_service.py`

Responsabilidade:

- manter o dia ativo em `session_state.json`
- permitir que a aplicacao trabalhe com a ideia de fluxo diario corrente

## 7. Interface por tela

### 7.1 Janela principal

Arquivo: `ui/app.py`

Responsabilidades:

- subir a janela
- montar a barra superior
- trocar entre telas
- atualizar status do dia ativo
- manter o topo em modo compacto como padrao

### 7.2 Painel diario

Arquivo: `ui/dashboard.py`

Responsabilidades:

- mostrar panorama do dia
- mostrar ultimas movimentacoes
- mostrar analise financeira do dia
- abrir anexos a partir da selecao

### 7.3 Novo registro

Arquivo: `ui/registro.py`

Responsabilidades:

- cadastrar entrada ou saida
- cadastrar `serviço técnico`
- escolher categoria, pessoa e metodo
- anexar arquivo
- preencher data com mascara
- calcular resumo de comissao em tempo real
- suportar um ou varios tecnicos no mesmo servico

### 7.4 Consultas e filtros

Arquivo: `ui/extrato.py`

Responsabilidades:

- aplicar filtros por texto, periodo, categoria, tipo e pessoa
- mostrar extrato em tabela
- abrir anexos do item selecionado

### 7.5 Cadastros

Arquivo: `ui/cadastros.py`

Responsabilidades:

- CRUD de categorias
- CRUD de pessoas/empresas
- CRUD de tecnicos/comissoes

### 7.6 Historico

Arquivo: `ui/historico.py`

Responsabilidades:

- escolher recorte por ano, mes ou dia
- abrir tela dedicada de leitura do periodo
- mostrar resumo, analise, grafico e registros
- editar e excluir registros
- exportar o periodo selecionado
- abrir anexos
- ordenar registros por clique no cabecalho

## 8. Componentes reutilizaveis

Arquivo: `ui/widgets.py`

Componentes importantes:

- `MarqueeLabel`
- `Card`
- `SectionFrame`
- `MetricBadge`
- `DetailMarqueeBar`
- `DateMaskEntry`
- `RegistryManagerFrame`
- `build_treeview_style()`

## 9. Exportacoes

### 9.1 Excel

Arquivo: `services/excel.py`

- gera `.xlsx` com Python puro
- nao depende de `openpyxl`

### 9.2 PDF

Arquivo: `services/pdf.py`

- gera `.pdf` com Python puro
- nao depende de `reportlab`

## 10. Portabilidade

O projeto foi ajustado para funcionar fora do ambiente de desenvolvimento:

- `core/app_paths.py` calcula caminhos em modo normal e congelado
- `FluxoDeCaixaDiario.spec` empacota recursos
- `build_exe.ps1` automatiza o build

## 11. Pontos de atencao

- A interface usa bastante `customtkinter`; alteracoes grandes de layout precisam de validacao visual.
- O historico e a tela mais sensivel da aplicacao e concentra muita regra de renderizacao.
- Os textos de interface devem permanecer coerentes com `entrada` e `saida`.
- Se houver ajustes em anexos, revisar tambem `services/attachments.py`.
- Em `serviço técnico`, nunca duplicar lucro com uma segunda entrada para o valor da empresa.
