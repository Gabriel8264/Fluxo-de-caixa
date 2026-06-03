# Indice oficial da documentacao

Este arquivo e o ponto de entrada oficial da documentacao do projeto.

Use este indice para:

- identificar quais documentos existem
- decidir o que precisa ser lido antes de cada alteracao
- localizar a fonte oficial de regras por modulo
- evitar regressao, quebra de legado e mudancas fora de escopo

## Documentos disponiveis

### `docs/ARQUITETURA.md`

Funcao:

- descrever a estrutura geral do sistema
- explicar camadas, inicializacao, persistencia e servicos
- registrar o estado atual das exportacoes e do fluxo de servico tecnico

Ler antes de:

- alterar `main.py`
- alterar `core/`
- alterar `services/`
- mexer em organizacao entre UI, servico e banco

### `docs/GABARITO_OPERACIONAL.md`

Funcao:

- definir o padrao de trabalho do projeto
- orientar manutencao com foco em resultado real, clareza e compatibilidade

Ler antes de:

- mudancas relevantes de comportamento
- refinamentos amplos de UX
- alteracoes que possam afetar legado, exportacao, dashboard ou historico

### `docs/GUIA_DE_MANUTENCAO.md`

Funcao:

- servir como guia pratico de manutencao
- indicar onde mexer para cada tipo de pedido
- consolidar checklists de validacao

Ler antes de:

- alterar telas da interface
- mexer em rolagem
- mexer em exportacao
- mexer em anexos
- mexer em filtros e tabelas

### `docs/HISTORICO.md`

Funcao:

- documentar especificamente a tela `Historico`
- explicar selecao de periodo, abas, scroll, registros, ordenacao e exportacao

Ler antes de:

- alterar `ui/historico.py`
- mexer em selecao por ano, mes ou dia
- mexer em `Resumo`, `Analise`, `Grafico` ou `Registros`
- mexer em exportacao acionada a partir do Historico

### `docs/SERVICO_TECNICO.md`

Funcao:

- documentar o fluxo de `servico tecnico`
- centralizar regras de comissao, multiplos tecnicos, persistencia e compatibilidade

Ler antes de:

- alterar `ui/registro.py`
- alterar `services/cash_service.py` no fluxo de servico tecnico
- alterar exportacoes que precisem mostrar tecnicos ou divisao de comissao

## Ordem recomendada de leitura

### Para entendimento geral

1. `docs/INDEX.md`
2. `docs/ARQUITETURA.md`
3. `docs/GABARITO_OPERACIONAL.md`
4. `docs/GUIA_DE_MANUTENCAO.md`

### Para manutencao normal

1. `docs/INDEX.md`
2. documento especifico da area afetada
3. `docs/GUIA_DE_MANUTENCAO.md` se houver implementacao pratica

### Para alteracoes no Historico

1. `docs/INDEX.md`
2. `docs/HISTORICO.md`
3. `docs/GUIA_DE_MANUTENCAO.md`
4. `docs/GABARITO_OPERACIONAL.md`

### Para alteracoes em servico tecnico

1. `docs/INDEX.md`
2. `docs/SERVICO_TECNICO.md`
3. `docs/ARQUITETURA.md`
4. `docs/GUIA_DE_MANUTENCAO.md`

## Guia rapido por area

### Arquitetura, banco, modelos ou servicos

Ler:

- `docs/INDEX.md`
- `docs/ARQUITETURA.md`
- `docs/GABARITO_OPERACIONAL.md`
- `docs/GUIA_DE_MANUTENCAO.md`

### Layout, navegacao ou widgets reutilizaveis

Ler:

- `docs/INDEX.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/GABARITO_OPERACIONAL.md`

### Novo registro, dashboard, cadastros, extrato ou anexos

Ler:

- `docs/INDEX.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/GABARITO_OPERACIONAL.md`

### Servico tecnico, tecnicos ou comissao

Ler:

- `docs/INDEX.md`
- `docs/SERVICO_TECNICO.md`
- `docs/ARQUITETURA.md`
- `docs/GUIA_DE_MANUTENCAO.md`

### Historico

Ler:

- `docs/INDEX.md`
- `docs/HISTORICO.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/GABARITO_OPERACIONAL.md`

### Exportacao Excel e PDF

Ler:

- `docs/INDEX.md`
- `docs/ARQUITETURA.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/SERVICO_TECNICO.md` se a exportacao precisar mostrar dados de tecnicos

## Regras obrigatorias

- Sempre ler `INDEX.md` antes de qualquer alteracao.
- Sempre ler a documentacao relacionada ao modulo que sera alterado.
- Considerar a documentacao como fonte oficial de verdade.
- Preservar compatibilidade com dados antigos.
- Nao criar regressao em funcionalidades existentes.
- Em caso de conflito entre documentacao e codigo, reportar o conflito antes de implementar.

## Limite de escopo

A documentacao deve orientar a tarefa atual, nao substituir a solicitacao do usuario.

Agentes de IA nao devem resolver problemas antigos, pendencias anteriores ou melhorias sugeridas na documentacao, a menos que a solicitacao atual peca isso explicitamente.

Ao ler a documentacao, use-a apenas para:

- entender regras
- evitar regressao
- localizar arquivos corretos
- validar compatibilidade

## Regras importantes repetidas nos documentos

### 1. Compatibilidade retroativa e obrigatoria

- registros antigos precisam continuar funcionando
- novos campos devem ter fallback seguro
- entradas e saidas antigas continuam validas
- ausencia de tecnico ou comissao nao pode quebrar leitura, exportacao, dashboard ou historico
- servicos antigos com um tecnico continuam validos

### 2. O fluxo financeiro nao pode ser distorcido

- nao duplicar lucro
- nao criar movimentacoes extras indevidas
- manter consistencia entre UI, servico, banco, dashboard, exportacao e fechamento mensal
- em `servico tecnico`, o valor da empresa e apenas resumo visual

### 3. Validar antes de entregar

- compilar modulos alterados
- instanciar `App()` quando possivel
- testar o fluxo principal afetado
- revisar impacto em historico, exportacao, filtros, dashboard e legado

### 4. Reduzir ruido visual

- cortar texto desnecessario
- evitar excesso de informacao simultanea
- aproximar blocos relacionados
- priorizar leitura objetiva e operacional

### 5. Evitar solucoes frageis

- preferir a menor area de mudanca possivel
- sistematizar quando o problema for recorrente
- evitar solucao improvisada para um caso local

### 6. Scroll e layout exigem cuidado especial

- evitar `bind_all` global
- evitar multiplos scrolls principais na mesma tela
- manter um unico scroll principal por tela, exceto tabelas
- mudancas visuais precisam de validacao em uso real

### 7. Tabelas administrativas seguem o mesmo padrao de ordenacao

- ordenacao por clique no cabecalho
- ciclo: sem ordenacao -> crescente -> decrescente -> sem ordenacao
- retorno para `sem ordenacao` usa a ordem original em memoria
- filtros ativos devem continuar valendo

### 8. O Historico e a area mais sensivel do sistema

- qualquer alteracao em `ui/historico.py` exige leitura previa da documentacao especifica
- testar selecao por ano, mes e dia
- testar todas as abas
- testar registros, edicao, exclusao, anexos e exportacoes

## Fonte oficial por tipo de decisao

### Estrutura e responsabilidade de modulos

Fonte principal:

- `docs/ARQUITETURA.md`

### Forma correta de conduzir manutencao

Fonte principal:

- `docs/GABARITO_OPERACIONAL.md`

### Onde mexer e como validar

Fonte principal:

- `docs/GUIA_DE_MANUTENCAO.md`

### Regras especificas da aba Historico

Fonte principal:

- `docs/HISTORICO.md`

### Regras especificas de servico tecnico

Fonte principal:

- `docs/SERVICO_TECNICO.md`

## Observacao final

Se novos documentos forem adicionados a pasta `docs`, este indice deve ser atualizado para continuar sendo o ponto de entrada oficial da documentacao do projeto.
