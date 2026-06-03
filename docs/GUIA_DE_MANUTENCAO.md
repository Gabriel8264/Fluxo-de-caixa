# Guia de manutencao rapida

Este arquivo acelera futuras alteracoes no projeto.

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

### Categorias, pessoas e tecnicos

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

Fluxo atual:

- rodar `.\build_exe.ps1`
- o script usa a virtualenv local e chama `PyInstaller`
- o resultado fica em `dist/`

## 2. Fluxo recomendado para alteracoes

1. Identificar a tela ou modulo afetado
2. Confirmar se a logica esta na UI ou no servico
3. Fazer a mudanca na menor area possivel
4. Pensar em impacto no resultado final e no legado
5. Validar compilacao
6. Instanciar `App()` para smoke test rapido
7. Se for mudanca visual, conferir uso real

## 3. Checklist de validacao rapida

### Sempre

- `.\.venv\Scripts\python.exe -m compileall ui services core`
- importar `App` e instanciar sem erro

### Se mexer em build do executavel

- rodar `.\build_exe.ps1`
- confirmar geracao do arquivo em `dist/`
- abrir o executavel para smoke test quando a mudanca afetar empacotamento, caminhos ou recursos

### Se mexer em UI

- conferir `wraplength`, `grid_columnconfigure` e `grid_rowconfigure`
- testar janela maximizada
- testar navegação entre telas

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
- abrir anexo
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
- confirmar que historico e dashboard continuam corretos
- confirmar exportacao Excel e PDF sem quebra

### Se mexer em exportacao

- testar exportacao diaria
- testar exportacao mensal
- testar exportacao anual
- testar poucos registros
- testar muitos registros
- testar descricoes longas
- testar anexos
- testar servico tecnico
- testar multiplos tecnicos

## 4. Convencoes do projeto

- tipos validos de movimentacao: `entrada` e `saida`
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
- renderizacao das abas
- tabela e detalhe de registros
- exportacao
- modal de edicao

Se a mudanca for grande, atuar por bloco e nao na tela inteira de uma vez.

### Rolagem

Hoje existem tres padroes de rolagem no projeto:

- `CTkScrollableFrame` com helper em `ui/widgets.py`
- `Canvas + scrollbar` no Historico principal
- `Treeview` com scroll proprio nas tabelas

Ao mexer em rolagem:

- evitar `bind_all` global
- evitar scroll duplicado na mesma area
- manter apenas um scroll principal por tela, exceto tabelas
- se houver `Treeview`, a roda em cima dela deve mover apenas a tabela
- no Historico, fora da tabela de `Registros`, a roda deve mover a pagina

### Textos com acentos

Sempre revisar os textos renderizados na interface, especialmente quando o terminal mostrar caracteres estranhos. A interface precisa continuar legivel em portugues.

### Servico tecnico

Regras operacionais importantes:

- `servico tecnico` e uma operacao propria
- se houver varios tecnicos, a comissao total e a soma dos percentuais individuais
- a divisao individual deve ser preservada para leitura futura
- nao recalcular servicos antigos automaticamente
- registros antigos sem tecnico ou sem comissao continuam validos
- a saida pode ser uma por tecnico, desde que o total nao duplique lucro

### Exportacao

Regras importantes:

- nao alterar dados do banco durante a exportacao
- respeitar o periodo selecionado no Historico
- manter compatibilidade com registros antigos
- exportacoes com tecnicos multiplos nao podem quebrar leitura
- melhorias visuais nao devem alterar regra financeira

## 6. Atalhos para pedidos comuns

### "Quero mais espaco na tela"

Revisar:

- `ui/app.py`
- `ui/historico.py`
- `ui/dashboard.py`

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

- a ordenacao segue ciclo de 3 estados
- `sem ordenacao -> crescente -> decrescente -> sem ordenacao`
- ao remover a ordenacao, voltar para a ordem original em memoria, sem novo fetch

### "Quero mudar exportacao"

Revisar:

- `services/excel.py`
- `services/pdf.py`
- `ui/historico.py`

### "Quero mudar o grafico"

Revisar:

- `ui/dashboard.py`
- `ui/historico.py`

### "Quero mudar o banco"

Revisar:

- `core/database.py`
- `core/models.py`
- `services/cash_service.py`
- `services/session_service.py` se houver impacto em persistencia local

### "Quero revisar compatibilidade com dados antigos"

Revisar:

- `core/database.py`
- `services/session_service.py`
- `database.py` na raiz se houver ponto de entrada legado
- `core/app_paths.py` se a mudanca envolver localizacao dos arquivos

Validar no minimo:

- banco antigo com tabela `movimentos` basica
- banco sem coluna `anexo`
- banco sem tabelas novas
- banco ja atualizado rodando migracao de novo
- `session_state.json` inexistente
- `session_state.json` vazio
- `session_state.json` invalido
- `session_state.json` com formato antigo de data
- `session_state.json` com campos extras

## 7. Sugestoes para futuras melhorias

- separar `ui/historico.py` em subcomponentes menores
- criar helpers reutilizaveis para fichas de detalhe
- centralizar textos da interface em modulo proprio
- adicionar testes automatizados para servicos e filtros
- documentar a exportacao em arquivo proprio se ela crescer mais

## 8. Observacao pratica sobre acentos

- o terminal pode mostrar UTF-8 de forma estranha em alguns contextos
- antes de corrigir texto, confirmar se o problema esta no arquivo fonte ou apenas na exibicao do terminal
- textos renderizados na interface devem permanecer corretos em portugues brasileiro
