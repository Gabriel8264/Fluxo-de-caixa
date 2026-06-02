# Guia de manutencao rapida

Este arquivo foi pensado para acelerar futuras alteracoes no projeto.

Complemento recomendado:

- `docs/GABARITO_OPERACIONAL.md`

## 1. Onde mexer em cada tipo de pedido

### Layout geral e navegacao

- `ui/app.py`
- `ui/theme.py`
- `ui/widgets.py`

### Painel diario

- `ui/dashboard.py`
- `services/cash_service.py`

### Novo registro

- `ui/registro.py`
- `services/cash_service.py`
- `core/database.py`

### Filtros e extrato

- `ui/extrato.py`
- `services/cash_service.py`
- `core/database.py`

### Categorias e pessoas

- `ui/cadastros.py`
- `ui/widgets.py`
- `services/cash_service.py`
- `core/database.py`

### Historico

- `ui/historico.py`
- `services/cash_service.py`
- `core/database.py`

### Anexos

- `services/attachments.py`
- `ui/registro.py`
- `ui/dashboard.py`
- `ui/extrato.py`
- `ui/historico.py`

### Exportacao Excel e PDF

- `services/excel.py`
- `services/pdf.py`
- `ui/historico.py`

### Build do executavel

- `build_exe.ps1`
- `FluxoDeCaixaDiario.spec`
- `core/app_paths.py`

## 2. Fluxo recomendado para alteracoes

1. Identificar a tela ou modulo afetado
2. Confirmar se a logica esta na UI ou no servico
3. Fazer a mudanca na menor area possivel
4. Pensar em impacto no resultado final do usuario e no legado
5. Validar compilacao
6. Instanciar `App()` para smoke test rapido
7. Se for mudanca visual, abrir a tela e conferir uso real

## 3. Checklist de validacao rapida

### Sempre

- `.\.venv\Scripts\python.exe -m compileall ui services core`
- importar `App` e instanciar sem erro

### Se mexer em UI

- conferir `wraplength`, `grid_columnconfigure`, `grid_rowconfigure`
- testar janela maximizada
- testar topo expandido e recolhido

### Se mexer em Historico

- testar selecao por `Ano`
- testar selecao por `Mes`
- testar selecao por `Dia`
- abrir `Resumo`
- abrir `Analise`
- abrir `Grafico`
- abrir `Registros`
- testar ordenacao por clique nos cabecalhos
- testar ciclo `sem ordenacao -> crescente -> decrescente -> sem ordenacao`
- selecionar um registro
- editar um registro
- excluir um registro
- exportar Excel
- exportar PDF

### Se mexer em anexos

- anexar em novo registro
- abrir anexo no registro
- abrir anexo no extrato
- abrir anexo no historico

### Se mexer em servico tecnico

- testar servico com um tecnico
- testar servico com multiplos tecnicos
- validar soma dos percentuais
- validar bloqueio acima de `100%`
- confirmar que o valor da empresa nao gera nova movimentacao
- confirmar que o historico e o dashboard continuam corretos
- confirmar exportacao Excel e PDF sem quebra

Leitura recomendada antes de mexer:

- `docs/SERVICO_TECNICO.md`

## 4. Convencoes do projeto

- tipos de movimentacao validos: `entrada` e `saida`
- data de armazenamento: `YYYY-MM-DD`
- data exibida: `DD/MM/YYYY`
- banco principal: `caixa.db`
- estado do dia ativo: `session_state.json`

## 5. Armadilhas conhecidas

### Compatibilidade antiga

`database.py` na raiz existe por legado. Se a mudanca for de regra de negocio, o lugar correto costuma ser `services/cash_service.py` ou `core/database.py`.

### Historico

`ui/historico.py` mistura:

- navegacao do recorte
- scroll principal da pagina
- renderizacao dos cards e blocos planos
- desenho dos graficos
- tabela e detalhe de registros
- modal de edicao

Se a mudanca for grande, vale atuar por bloco e nao em tudo ao mesmo tempo.

### Rolagem

Hoje existem tres padroes de rolagem no projeto:

- `CTkScrollableFrame` com bind helper em `ui/widgets.py`
- `Canvas + scrollbar` no Historico principal
- `Treeview` com scroll proprio nas tabelas

Ao mexer em rolagem:

- evitar `bind_all` global
- evitar scroll duplicado na mesma area
- manter apenas um scroll principal por tela, exceto tabelas
- se houver tabela `Treeview`, a roda do mouse em cima dela deve mover apenas a tabela
- no Historico, fora da tabela de `Registros`, a roda deve mover a pagina

### Textos com acentos

Sempre revisar os textos renderizados na interface, especialmente quando o console mostrar caracteres estranhos. A interface precisa continuar legivel em portugues.

### Servico tecnico

Regras operacionais importantes:

- `serviço técnico` e uma operacao propria
- se houver varios tecnicos, a comissao total e a soma dos percentuais individuais
- a divisao individual deve ser preservada para leitura futura
- nao recalcular servicos antigos automaticamente
- registros antigos sem tecnico ou sem comissao continuam validos
- a saida pode ser uma por tecnico, desde que o total nao duplique lucro

### Layout

Evite colocar muita informacao na mesma linha. Em telas densas, prefira:

- cards em colunas
- painel lateral de detalhe
- submenus em `Tabview`
- botoes de recolher areas grandes

## 6. Atalhos para pedidos comuns

### "Quero mais espaco na tela"

Revisar:

- `ui/app.py` para topo
- `ui/historico.py` para cards e paines laterais
- `ui/dashboard.py` para distribuicao dos blocos

### "Quero mais filtros"

Revisar:

- `ui/extrato.py`
- `services/cash_service.py:list_movements`
- `core/database.py:fetch_movements`

### "Quero mudar ordenacao de tabelas"

Revisar:

- `ui/historico.py` para `Registros`
- `ui/extrato.py` para `Consultas e filtros`

Lembrar:

- a ordenacao hoje segue ciclo de 3 estados
- `sem ordenacao -> crescente -> decrescente -> sem ordenacao`
- ao remover a ordenacao, voltar para a ordem original em memoria, sem novo fetch

### "Quero mudar o grafico"

Revisar:

- `ui/dashboard.py` para painel diario
- `ui/historico.py` para historico

### "Quero mudar o banco"

Revisar:

- `core/database.py`
- `core/models.py`
- `services/cash_service.py`

## 7. Sugestoes para futuras melhorias

- separar `ui/historico.py` em subcomponentes menores
- criar helpers reutilizaveis para cards de detalhe
- centralizar textos da interface em um modulo proprio
- adicionar testes automatizados para servicos e filtros
