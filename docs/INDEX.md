# Índice oficial da documentação

Este arquivo é o ponto de entrada oficial da documentação do projeto.

Antes de qualquer alteração, leitura de contexto, manutenção ou refatoração, este documento deve ser consultado para orientar:

- quais arquivos de documentação existem
- quando cada documento deve ser lido
- quais regras são obrigatórias
- quais cuidados preservar em dados, interface e fluxo financeiro

## Documentos disponíveis

### `docs/ARQUITETURA.md`

Função:

- explicar a arquitetura geral do projeto
- descrever camadas, fluxo de inicialização, persistência, serviços e responsabilidades da interface
- registrar a estrutura atual do fluxo de `serviço técnico` e dos dados persistidos

Quando consultar:

- antes de alterações estruturais
- antes de mexer em camadas de serviço, banco ou navegação principal
- quando houver dúvida sobre onde uma regra deve ficar

Agentes de IA devem ler antes de:

- modificar `main.py`
- modificar `core/`
- modificar `services/`
- alterar organização entre UI, serviço e persistência

### `docs/GABARITO_OPERACIONAL.md`

Função:

- definir o padrão operacional de trabalho no projeto
- orientar manutenção com foco em resultado real, validação, clareza e compatibilidade

Quando consultar:

- antes de mudanças relevantes
- antes de concluir tarefas que afetam fluxo financeiro, usabilidade ou layout
- quando houver dúvida sobre profundidade da validação

Agentes de IA devem ler antes de:

- qualquer alteração relevante de comportamento
- mudanças em telas sensíveis
- mudanças que possam afetar legado, exportação, dashboard ou histórico

### `docs/GUIA_DE_MANUTENCAO.md`

Função:

- servir como guia rápido de manutenção
- indicar onde mexer para cada tipo de pedido
- fornecer checklists de validação e armadilhas conhecidas
- consolidar cuidados práticos com rolagem, ordenação e compatibilidade retroativa

Quando consultar:

- ao iniciar tarefas práticas de manutenção
- ao decidir quais arquivos alterar
- antes de validar UI, histórico, anexos, exportação ou rolagem

Agentes de IA devem ler antes de:

- alterar qualquer tela da interface
- mexer em rolagem
- mexer em exportação
- mexer em anexos
- mexer em filtros e extratos

### `docs/HISTORICO.md`

Função:

- documentar especificamente a aba `Histórico`
- explicar seleção de período, abas, estratégia de scroll, registros, ordenação, detalhes e pontos sensíveis

Quando consultar:

- antes de qualquer alteração em `ui/historico.py`
- antes de mexer em seleção por ano, mês ou dia
- antes de mexer em resumo, análise, gráfico, registros, edição ou exportação do histórico

Agentes de IA devem ler antes de:

- modificar a tela `Histórico`
- alterar a estratégia de scroll do histórico
- alterar renderização das abas do histórico
- alterar tabela, filtros, detalhes ou exportações do histórico

### `docs/SERVICO_TECNICO.md`

Função:

- documentar o fluxo de `servico tecnico`
- centralizar regras de comissao, multiplos tecnicos, persistencia e compatibilidade

Quando consultar:

- antes de qualquer alteracao em `ui/registro.py`
- antes de mexer em tecnicos, comissao ou resumo visual do servico
- antes de alterar como o sistema salva ou exibe divisao de comissao

Agentes de IA devem ler antes de:

- modificar `services/cash_service.py` no fluxo de servico tecnico
- modificar `ui/registro.py`
- modificar exportacoes que precisem mostrar tecnicos

## Ordem recomendada de leitura

### Para entendimento geral do projeto

1. `docs/INDEX.md`
2. `docs/ARQUITETURA.md`
3. `docs/GABARITO_OPERACIONAL.md`
4. `docs/GUIA_DE_MANUTENCAO.md`

### Para manutenção normal

1. `docs/INDEX.md`
2. `docs/GUIA_DE_MANUTENCAO.md`
3. documentação específica da área afetada

### Para alterações no Histórico

1. `docs/INDEX.md`
2. `docs/HISTORICO.md`
3. `docs/GUIA_DE_MANUTENCAO.md`
4. `docs/GABARITO_OPERACIONAL.md`
5. `docs/ARQUITETURA.md` se houver impacto estrutural

## Guia rápido por área do sistema

### Se for alterar arquitetura, banco, modelos ou serviços

Ler:

- `docs/INDEX.md`
- `docs/ARQUITETURA.md`
- `docs/GABARITO_OPERACIONAL.md`
- `docs/GUIA_DE_MANUTENCAO.md`

### Se for alterar layout, navegação ou widgets reutilizáveis

Ler:

- `docs/INDEX.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/GABARITO_OPERACIONAL.md`

### Se for alterar Novo registro, Dashboard, Cadastros, Extrato ou Anexos

Ler:

- `docs/INDEX.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/GABARITO_OPERACIONAL.md`
- `docs/ARQUITETURA.md` se a alteração tocar serviço ou persistência

### Se for alterar serviço técnico, técnicos ou comissão

Ler:

- `docs/INDEX.md`
- `docs/SERVICO_TECNICO.md`
- `docs/ARQUITETURA.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/GABARITO_OPERACIONAL.md`

### Se for alterar Histórico

Ler:

- `docs/INDEX.md`
- `docs/HISTORICO.md`
- `docs/GUIA_DE_MANUTENCAO.md`
- `docs/GABARITO_OPERACIONAL.md`

## Regras obrigatórias

- Sempre ler `INDEX.md` antes de qualquer alteração.
- Sempre ler a documentação relacionada ao módulo que será alterado.
- Considerar a documentação como fonte oficial de verdade.
- Preservar compatibilidade com dados antigos.
- Não criar regressões em funcionalidades existentes.
- Em caso de conflito entre documentação e código, reportar o conflito antes de implementar.

## Limite de escopo

A documentação deve orientar a tarefa atual, não substituir a solicitação do usuário.

Agentes de IA não devem resolver problemas antigos, pendências anteriores ou melhorias sugeridas na documentação, a menos que a solicitação atual peça isso explicitamente.

Ao ler a documentação, use-a apenas para:

- entender regras
- evitar regressões
- localizar arquivos corretos
- validar compatibilidade

## Regras importantes repetidas na documentação

Estas regras aparecem de forma recorrente nos documentos existentes e devem ser tratadas como diretrizes fortes do projeto:

### 1. Compatibilidade retroativa é obrigatória

- registros antigos precisam continuar funcionando
- novos campos devem ter fallback seguro
- entradas e saídas antigas continuam válidas
- ausência de técnico ou comissão não pode quebrar leitura, exportação, dashboard ou histórico
- serviços antigos com um técnico continuam válidos

### 2. O fluxo financeiro não pode ser distorcido

- não duplicar lucro
- não criar movimentações extras indevidas
- manter consistência entre UI, serviço, banco, dashboard, exportação e fechamento mensal
- em `serviço técnico`, o valor da empresa é apenas resumo visual

### 3. Validar antes de entregar

- compilar módulos alterados
- instanciar `App()` quando possível
- testar o fluxo principal afetado
- revisar impacto em histórico, exportação, filtros, dashboard e legado

### 4. Reduzir ruído visual

- cortar texto desnecessário
- evitar excesso de informação simultânea
- aproximar blocos relacionados
- priorizar leitura objetiva e operacional

### 5. Evitar soluções frágeis

- preferir a menor área de mudança possível
- sistematizar quando o problema for recorrente
- evitar soluções improvisadas que resolvem só um caso local

### 6. Scroll e layout exigem cuidado especial

- evitar `bind_all` global
- evitar múltiplos scrolls principais na mesma tela
- manter um único scroll principal por tela, exceto tabelas
- mudanças visuais precisam de validação em uso real

### 7. Tabelas administrativas seguem o mesmo padrão de ordenação

- ordenação por clique no cabeçalho
- ciclo: sem ordenação -> crescente -> decrescente -> sem ordenação
- o retorno a `sem ordenação` usa a ordem original em memória
- filtros ativos devem continuar valendo

### 8. O Histórico é a área mais sensível do sistema

- qualquer alteração em `ui/historico.py` exige leitura prévia da documentação específica
- testar seleção por ano, mês e dia
- testar todas as abas
- testar registros, edição, exclusão, anexos e exportações

## Fonte oficial por tipo de decisão

### Estrutura e responsabilidade de módulos

Fonte principal:

- `docs/ARQUITETURA.md`

### Forma correta de conduzir manutenção

Fonte principal:

- `docs/GABARITO_OPERACIONAL.md`

### Onde mexer e como validar

Fonte principal:

- `docs/GUIA_DE_MANUTENCAO.md`

### Regras específicas da aba Histórico

Fonte principal:

- `docs/HISTORICO.md`

### Regras específicas de serviço técnico

Fonte principal:

- `docs/SERVICO_TECNICO.md`

## Conduta esperada de agentes de IA

Antes de alterar qualquer parte do projeto, agentes de IA devem:

1. Ler `docs/INDEX.md`.
2. Identificar a área afetada.
3. Ler o documento específico correspondente.
4. Confirmar impacto em legado, fluxo financeiro, exportação e dashboard.
5. Executar a mudança na menor superfície possível.
6. Validar compilação e fluxo principal.
7. Reportar conflitos entre documentação e código antes de implementar.

## Observação final

Se novos documentos forem adicionados à pasta `docs`, este índice deve ser atualizado para continuar sendo o ponto de entrada oficial da documentação do projeto.
