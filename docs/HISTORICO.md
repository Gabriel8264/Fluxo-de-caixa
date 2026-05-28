# Aba Historico

Este documento explica a estrutura atual da aba `Historico`, que hoje e a parte mais complexa da interface.

Arquivo principal:

- `ui/historico.py`

## 1. Objetivo da tela

Permitir leitura do historico por:

- ano
- mes
- dia

Cada periodo abre uma tela de leitura com:

- `Resumo`
- `Analise`
- `Grafico`
- `Registros`

## 2. Estrutura visual atual

### Etapa 1: selecao

Primeira tela exibida:

- seletor de `Nivel de leitura`
- menu de `Ano`
- menu de `Mes`
- menu de `Dia`
- preview textual do periodo
- botao `Abrir visao ...`

Metodos principais:

- `_build_selection_screen`
- `_populate_selector_menus`
- `_handle_scope_change`
- `_on_year_selected`
- `_on_month_selected`
- `_on_day_selected`
- `_update_selection_preview`

### Etapa 2: leitura do periodo

Segunda tela exibida:

- botao `Voltar`
- titulo do periodo
- subtitulo orientativo
- faixa de metricas
- abas de conteudo

Metodos principais:

- `_build_detail_screen`
- `_show_scope_details`
- `_load_scope_data`
- `_render_detail_header`
- `_render_metric_strip`

## 3. Dados usados pela tela

A tela nao monta os dados diretamente do banco. Ela consome o pacote pronto retornado por:

- `services/cash_service.py:get_history_scope_data`

Esse pacote traz:

- `scope`
- `label`
- `start_date`
- `end_date`
- `movements`
- `summary`
- `timeline`

## 4. Aba Resumo

Responsavel por leitura executiva do periodo.

Metodos principais:

- `_render_summary_tab`
- `_build_overview_text`
- `_build_distribution_text`
- `_build_highlights_text`
- `_build_rhythm_text`

Quando alterar:

- revisar textos
- revisar cards
- evitar excesso de informacao em um unico bloco

## 5. Aba Analise

Responsavel por interpretacao do periodo.

Metodos principais:

- `_render_analysis_tab`
- `_build_financial_diagnostic`
- `_build_type_analysis`
- `_group_values`
- `_format_rank_items`

Quando alterar:

- manter foco em leitura humana
- priorizar diagnostico e nao apenas numeros crus

## 6. Aba Grafico

Responsavel por graficos desenhados em `tk.Canvas`.

### Visao anual e mensal

Usa:

- `_draw_timeline_chart`
- `_render_chart_sidebar_for_timeline`

Leitura:

- barras de entradas e saidas
- linha de saldo
- cards laterais explicativos

### Visao diaria

Usa:

- `_draw_composition_chart`
- `_draw_horizontal_group`
- `_render_chart_sidebar_for_day`

Leitura:

- cards de entradas, saidas e saldo
- barras por categoria
- barras por metodo
- leitura auxiliar ao lado

Quando alterar o grafico:

- testar em resolucoes menores
- evitar sobrepor texto com barras
- limitar quantidade de itens exibidos
- manter contraste alto

## 7. Aba Registros

Responsavel pela conferencia detalhada dos lancamentos do periodo.

Estrutura atual:

- barra de busca
- filtro por tipo
- ordenacao
- tabela resumida
- painel lateral com detalhes completos
- acoes de editar, excluir, exportar e abrir anexo

Metodos principais:

- `_build_records_tab`
- `_render_records`
- `_filtered_scope_movements`
- `_sort_records_by_column`
- `_update_selected_detail`
- `_reset_records_state`

### Edicao

Modal:

- `MovementEditorDialog`

Integracoes:

- `CashService.update_movement`
- `CashService.delete_movement`

## 8. Fluxo de selecao

### Ano

1. selecionar `Ano`
2. escolher o ano
3. tela abre leitura anual

### Mes

1. selecionar `Mes`
2. escolher ano
3. escolher mes
4. tela abre leitura mensal

### Dia

1. selecionar `Dia`
2. escolher ano
3. escolher mes
4. escolher dia
5. tela abre leitura diaria

## 9. Pontos sensiveis

- `ui/historico.py` e grande e concentra varias responsabilidades
- alteracoes pequenas de layout podem afetar muitos grids
- `Canvas` exige cuidado manual com coordenadas e espacamento
- a aba `Registros` precisa equilibrar legibilidade da tabela com o painel lateral

## 10. Recomendacoes para futuras refatoracoes

Se a aba crescer mais, o ideal e separar em:

- `HistorySelectionView`
- `HistorySummaryPanel`
- `HistoryAnalysisPanel`
- `HistoryChartPanel`
- `HistoryRecordsPanel`
- `MovementEditorDialog`

Isso reduziria o tamanho de `ui/historico.py` e facilitaria manutencao por bloco.
