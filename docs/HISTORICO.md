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

## 2. Estrutura geral atual

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

O Historico nao usa mais `CTkScrollableFrame` como container principal.

Hoje a tela usa:

- `tk.Canvas` como area principal de rolagem
- `CTkScrollbar` vertical ligada ao canvas
- um unico fluxo principal de scroll para a pagina

Excecao:

- a tabela de `Registros` usa `Treeview` com scroll proprio

Regras atuais:

- fora da tabela, a roda do mouse move a pagina do Historico
- em cima da tabela, a roda do mouse move apenas a tabela
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

## 6. Aba Analise

Responsavel pela leitura mais interpretativa do periodo.

Exibe indicadores como:

- saldo liquido
- peso das saidas sobre entradas
- medias
- participacao por categoria
- quantidade de entradas
- quantidade de saidas

Metodo principal:

- `_render_analysis_tab`

## 7. Aba Grafico

Responsavel pelas leituras visuais do periodo.

Hoje a implementacao foi simplificada para estabilidade visual.

Usa:

- barras com `CTkProgressBar`
- grupos resumidos por categoria
- comparacao entre entradas, saidas e saldo

Metodo principal:

- `_render_chart_tab`

Observacao:

- esta aba deve priorizar estabilidade e leitura objetiva
- evitar excesso de itens visuais no mesmo bloco

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
- ordenacao

Metodos principais:

- `_build_records_tab`
- `_render_records_tab`
- `_apply_record_filters`
- `_render_records`
- `_render_selected_movement`

## 9. Detalhes do registro

Os detalhes do registro nao usam mais varios cards grandes separados.

Hoje a leitura e uma ficha compacta unica:

- linha superior com `Data · Tipo · Categoria`
- valor destacado
- campos abaixo:
  - `Pessoa / empresa`
  - `Metodo`
  - `Descricao`
  - `Anexo`

Regras:

- se houver anexo, o botao `Abrir anexo` da barra de acoes fica habilitado
- se nao houver selecao, aparece uma mensagem simples

## 10. Exportacao e edicao

Na aba `Registros`:

- editar registro
- excluir registro
- abrir anexo
- exportar Excel
- exportar PDF

Modal de edicao:

- `MovementEditorDialog`

Esse modal usa `CTkScrollableFrame` proprio e bind de roda do mouse aplicado por helper.

## 11. Pontos sensiveis

- `ui/historico.py` continua grande
- a tela mistura selecao, leitura, filtros, tabela, exportacao e modal
- qualquer alteracao de layout deve ser testada com muito conteudo
- a rolagem principal do Historico nao deve voltar a usar binds globais

## 12. Checklist recomendado ao mexer no Historico

- abrir selecao por `Ano`
- abrir selecao por `Mes`
- abrir selecao por `Dia`
- trocar entre todas as abas
- rolar a pagina fora da tabela
- rolar a tabela de registros separadamente
- testar com 10 registros
- testar com 50 registros
- testar com 100 registros
- editar um registro
- excluir um registro
- abrir anexo
- exportar Excel
- exportar PDF

## 13. Direcao recomendada para futuras melhorias

Se a tela crescer mais, separar em modulos menores:

- `HistorySelectionPanel`
- `HistorySummaryPanel`
- `HistoryAnalysisPanel`
- `HistoryChartPanel`
- `HistoryRecordsPanel`
- `MovementEditorDialog`

Isso reduziria a complexidade de `ui/historico.py` e deixaria manutencao mais previsivel.
