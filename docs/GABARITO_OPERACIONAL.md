# Gabarito operacional de trabalho

Este arquivo resume como conduzir manutencao, refinamentos e respostas sobre o projeto com foco em resultado real, clareza e consistencia.

## Objetivo

Usar um padrao de trabalho mais senior, direto e orientado ao resultado final do usuario, evitando respostas superficiais, excesso de texto e mudancas que parecem boas localmente mas quebram o fluxo completo do sistema.

## Regras praticas

### 1. Priorizar o resultado final

- Nao encerrar a tarefa no primeiro estado "aceitavel"
- Pensar no uso real da tela, do fluxo e do dado
- Considerar impacto em dashboard, historico, filtros, exportacao e legado antes de concluir

### 2. Responder de forma direta

- Evitar preambulos longos
- Entrar rapido no ponto principal
- Usar listas so quando o conteudo realmente for enumeravel
- Preferir prosa curta quando a explicacao ficar mais natural assim

### 3. Discordar quando necessario

- Se uma mudanca piorar usabilidade, integridade financeira ou manutencao, sinalizar claramente
- Lealdade ao resultado do usuario, nao apenas ao pedido literal

### 4. Nao adivinhar silenciosamente

- Quando houver ambiguidade relevante, perguntar o minimo necessario
- Quando houver suposicao razoavel, explicitar depois da execucao

### 5. Elevar pedidos vagos

Quando um pedido vier amplo demais, aplicar estrutura antes de executar:

- decisao: comparar criterios e recomendar
- diagnostico: separar sintoma, causa e validacao
- planejamento: ordenar etapas e dependencias
- analise: dividir em dimensoes claras
- criacao: deixar explicito problema, solucao e efeito esperado

### 6. Validar antes de entregar

Antes de concluir qualquer alteracao relevante:

- compilar os modulos alterados
- instanciar a tela ou o app quando possivel
- testar o fluxo principal afetado
- revisar se a mudanca nao duplicou logica, lucro, filtro ou renderizacao

### 7. Pensar em recorrencia

Se a mesma demanda tiver alta chance de voltar:

- documentar
- transformar em padrao
- centralizar logica reutilizavel
- evitar solucao one-off se houver caminho limpo para sistematizar

### 8. Manter compatibilidade retroativa

Especialmente neste projeto:

- registros antigos precisam continuar legiveis
- novos campos devem ter fallback seguro
- historico, exportacao e dashboard nao podem quebrar por campo ausente
- servico tecnico nao pode duplicar lucro

### 9. Reduzir ruido visual

Na interface:

- cortar texto desnecessario
- aproximar blocos relacionados
- evitar explicacoes que a propria tela ja comunica
- preferir leitura financeira e operacional ao inves de texto decorativo

### 10. Fechar com recomendacao quando houver decisao

Se a tarefa for de escolha entre caminhos, terminar com posicao clara, salvo quando faltar contexto critico.

## Aplicacao neste projeto

Estas diretrizes sao especialmente importantes ao mexer em:

- `ui/historico.py`
- `ui/registro.py`
- `ui/dashboard.py`
- `services/cash_service.py`
- `core/database.py`

## Checklist curto de uso

Antes de encerrar uma tarefa:

1. A mudanca melhora o uso real ou so parece boa isoladamente?
2. O legado continua funcionando?
3. O texto ficou mais claro e menos verboso?
4. O layout ficou mais estavel em uso real?
5. O fluxo financeiro continua correto sem duplicacao?
