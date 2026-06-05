# Aba Historico

Este documento descreve a implementacao atual da aba `Historico`.

Arquivo principal:

- `ui/historico.py`

## 1. Objetivo da tela

Permitir leitura financeira por:

- ano
- mes
- dia

Cada periodo abre uma leitura dedicada com:

- `Resumo`
- `Analise`
- `Grafico`
- `Registros`

## 2. Estrutura geral

### Tela 1: selecao do periodo

Exibe:

- seletor de `Nivel de leitura`
- seletor de `Ano`
- seletor de `Mes`
- seletor de `Dia`
- preview do periodo
- botao `Abrir periodo`

Metodos principais:

- `_build_selection_screen`
- `_refresh_selectors`
- `_render_selection_preview`
- `_on_scope_change`
- `_on_year_selected`
- `_on_month_selected`
- `_on_day_selected`

### Tela 2: leitura do periodo

Exibe:

- botao `Voltar`
- titulo do periodo
- subtitulo com intervalo
- seletor manual de abas
- painel de conteudo da aba ativa

Metodos principais:

- `_build_detail_screen`
- `_open_scope`
- `_render_scope_data`
- `_show_tab`
- `_render_active_tab`

## 3. Estrategia de scroll

O Historico nao usa `CTkScrollableFrame` como container principal.

Hoje a tela usa:

- `tk.Canvas` como area principal de rolagem
- `CTkScrollbar` vertical ligada ao canvas
- um unico fluxo principal de scroll para a pagina

Excecao:

- a tabela de `Registros` usa `Treeview` com scroll proprio

Regras atuais:

- fora da tabela, a roda move a pagina do Historico
- em cima da tabela, a roda move apenas a tabela
- evitar `bind_all` global
- evitar mais de um scroll principal na mesma tela

Pontos principais no codigo:

- `HistoryView.__init__`
- `_sync_scroll_region`
- `_sync_viewport_width`
- `_on_mousewheel`
- `_bind_history_mousewheel`

## 4. Dados usados pela tela

A tela recebe um pacote consolidado do servico:

- `services/cash_service.py:get_history_scope_data`

Campos esperados:

- `scope`
- `label`
- `start_date`
- `end_date`
- `movements`
- `summary`
- `timeline`

Compatibilidade:

- registros antigos sem tecnico continuam validos
- registros antigos sem comissao continuam validos
- entradas e saidas antigas continuam validas
- categoria antiga `Comissao` continua valida

## 5. Aba Resumo

Entrega leitura financeira rapida do periodo.

Blocos atuais:

- `Resumo do periodo`
- `Leitura do periodo`
- `Destaques das entradas`
- `Destaques das saidas`
- `Origem do dinheiro`
- `Destino do dinheiro`
- `Sintese do fechamento`

Metodo principal:

- `_render_summary_tab`

Objetivo:

- mostrar quanto entrou
- mostrar quanto saiu
- mostrar saldo
- apontar principais origens e destinos do dinheiro
- manter foco em leitura consolidada

## 6. Aba Analise

Responsavel pela leitura mais interpretativa do periodo.

Exibe indicadores como:

- saldo liquido
- peso das saidas sobre entradas
- medias
- participacao por categoria
- quantidade de entradas
- quantidade de saidas
- relacao entre entradas e saidas

Metodo principal:

- `_render_analysis_tab`

## 7. Aba Grafico

Responsavel pelas leituras visuais do periodo.

Usa:

- barras com `CTkProgressBar`
- grupos resumidos por categoria
- comparacao entre entradas, saidas e saldo
- evolucao temporal simplificada quando houver dados suficientes

Metodo principal:

- `_render_chart_tab`

Regra:

- priorizar estabilidade e leitura objetiva

## 8. Aba Registros

Responsavel pela conferencia detalhada dos lancamentos.

Estrutura atual:

- bloco `Filtros`
- bloco `Movimentacoes` com `Treeview`
- barra de acoes
- ficha compacta `Detalhes do registro`

Filtros atuais:

- descricao
- tipo
- categoria
- pessoa
- metodo
- data

Ordenacao atual:

- feita pelos cabecalhos da tabela
- colunas ordenaveis:
  - `Data`
  - `Tipo`
  - `Valor`
  - `Categoria`
  - `Descricao`
  - `Pessoa / empresa`
  - `Metodo`
  - `Anexo`
- ciclo:
  - sem ordenacao
  - crescente
  - decrescente
  - sem ordenacao
- retorno para `sem ordenacao` usa a ordem original em memoria
- filtros ativos devem continuar valendo

Metodos principais:

- `_build_records_tab`
- `_render_records_tab`
- `_apply_record_filters`
- `_render_records`
- `_render_selected_movement`

Ao editar um registro, o campo `Valor` usa `MoneyMaskEntry` e deve exibir valores carregados no padrao brasileiro (`120.0` -> `120,00`, `1.234,56`). A mascara trata inteiros como reais, usa virgula como separador decimal, interpreta ponto como milhar em entradas como `2.000` e aceita ponto decimal apenas em entrada simples como `12.50`. Antes de salvar, o campo deve chamar `format_current()`; o servico normaliza o valor para `float` com a conversao central de `core/money.py`.

## 9. Detalhes do registro

Os detalhes do registro usam uma ficha compacta unica:

- linha superior com `Data · Tipo · Categoria`
- valor destacado
- campos abaixo:
  - `Pessoa / empresa`
  - `Metodo`
  - `Descricao`
  - `Anexo`

Regras:

- se houver anexo, o botao `Abrir anexo` fica habilitado
- se nao houver selecao, aparece uma mensagem simples
- se o registro continuar existindo apos filtro ou ordenacao, a selecao deve ser preservada quando possivel

## 10. Exportacao e edicao

Na aba `Registros`:

- editar registro
- excluir registro
- abrir anexo
- exportar Excel
- exportar PDF

Modal de edicao:

- `MovementEditorDialog`

Esse modal usa `CTkScrollableFrame` proprio e bind de roda aplicado por helper.

Compatibilidade importante ao editar:

- editar um registro antigo nao pode contaminar o dia ativo atual
- o registro deve continuar vinculado a sua data real
- so deve impactar o painel diario atual se a data for alterada para o dia ativo

## 11. Exportacao pelo Historico

O Historico e o ponto de acionamento da exportacao do periodo selecionado.

Regras atuais:

- a exportacao deve respeitar exatamente o periodo selecionado
- o escopo pode ser diario, mensal ou anual
- `ui/historico.py` repassa movimentos e metadados para:
  - `services/excel.py`
  - `services/pdf.py`

Os metadados repassados incluem:

- tipo da exportacao
- label do periodo
- data de geracao
- resumo do periodo

## 12. Compatibilidade financeira e legado

O Historico precisa continuar legivel com:

- entradas antigas
- saidas antigas
- registros sem tecnico
- registros sem comissao
- categoria antiga `Comissao`
- servicos tecnicos antigos com um unico tecnico
- servicos tecnicos novos com multiplos tecnicos

Regras financeiras importantes:

- `servico tecnico` gera entrada bruta do servico
- a comissao entra como saida
- o valor da empresa nunca vira nova entrada
- multiplos tecnicos nao podem duplicar lucro

Quando houver varios tecnicos:

- a divisao deve poder ser lida na interface
- a exportacao nao pode quebrar
- os registros antigos continuam funcionando sem migracao obrigatoria

## 13. Pontos sensiveis

- `ui/historico.py` continua grande
- a tela mistura selecao, leitura, tabela, exportacao e modal
- qualquer alteracao de layout deve ser testada com muito conteudo
- a rolagem principal nao deve voltar a usar bind global
- dropdowns customizados de `Ano`, `Mes` e `Dia` exigem teste de alternancia e clique fora
- a tabela de `Registros` e o scroll principal nao devem brigar entre si

## 14. Checklist ao mexer no Historico

- abrir selecao por `Ano`
- abrir selecao por `Mes`
- abrir selecao por `Dia`
- testar abrir e fechar dropdown com segundo clique
- testar clique fora para fechar dropdown
- trocar entre todas as abas
- rolar a pagina fora da tabela
- rolar a tabela separadamente
- testar com 10 registros
- testar com 50 registros
- testar com 100 registros
- testar ordenacao dos cabecalhos
- testar retorno para `sem ordenacao`
- editar um registro
- excluir um registro
- abrir anexo
- exportar Excel
- exportar PDF

## 15. Direcao recomendada para o futuro

Se a tela crescer mais, separar em modulos menores:

- `HistorySelectionPanel`
- `HistorySummaryPanel`
- `HistoryAnalysisPanel`
- `HistoryChartPanel`
- `HistoryRecordsPanel`
- `MovementEditorDialog`

Isso reduz a complexidade de `ui/historico.py` e deixa a manutencao mais previsivel.
