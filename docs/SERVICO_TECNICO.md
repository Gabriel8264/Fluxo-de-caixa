# Servico tecnico

Este documento concentra as regras do fluxo de `servico tecnico`.

Arquivos mais importantes:

- `ui/registro.py`
- `services/cash_service.py`
- `core/database.py`
- `core/models.py`
- `services/excel.py`
- `services/pdf.py`
- `ui/historico.py`

## 1. Objetivo

O modo `servico tecnico` existe para registrar servicos que geram:

- uma entrada bruta do servico
- uma ou mais saidas de comissao

Esse fluxo permite:

- calcular o lucro real naturalmente
- registrar um ou varios tecnicos
- manter compatibilidade com dashboard, historico, exportacoes e fechamento mensal

## 2. Regras financeiras principais

### 2.1 Fluxo correto

Um `servico tecnico` deve gerar apenas:

- `+ entrada bruta do servico`
- `- saida da comissao`

O valor da empresa:

- e apenas resumo visual
- nao pode virar nova entrada

### 2.2 Fluxo proibido

Nunca registrar:

- entrada do servico
- saida da comissao
- entrada extra para o valor da empresa

Isso duplicaria o lucro e quebraria:

- dashboard
- historico
- exportacoes
- fechamento mensal

## 3. Tecnico unico e multiplos tecnicos

O sistema deve aceitar:

- servicos antigos com um tecnico
- servicos novos com um ou varios tecnicos

Se houver varios tecnicos:

- cada tecnico usa seu proprio percentual
- a comissao total e a soma dos percentuais individuais

Exemplo:

- valor do servico: `R$ 100,00`
- Gabriel: `30%`
- Jose: `30%`

Resultado correto:

- comissao total: `60%`
- Gabriel: `R$ 30,00`
- Jose: `R$ 30,00`
- empresa: `R$ 40,00`

## 4. Calculo correto

### 4.1 Percentual total

`percentual_total_comissao = soma(percentuais dos tecnicos selecionados)`

### 4.2 Comissao total

`comissao_total = valor_servico * percentual_total_comissao / 100`

### 4.3 Valor individual por tecnico

`valor_tecnico = valor_servico * percentual_tecnico / 100`

### 4.4 Valor da empresa

`valor_empresa = valor_servico - comissao_total`

## 5. Validacoes obrigatorias

- nao permitir salvar servico tecnico sem tecnico selecionado
- nao permitir tecnico duplicado no mesmo servico
- nao permitir tecnicos inativos
- nao permitir soma de percentuais acima de `100%`

Mensagem esperada para excesso:

- `A soma das comissoes dos tecnicos nao pode ultrapassar 100%.`

Se nenhum tecnico estiver selecionado:

- comissao total = `R$ 0,00`
- percentual da empresa = `100%`
- valor da empresa = valor total do servico
- mas o salvamento continua bloqueado

## 6. Persistencia

Ao salvar um servico tecnico, o sistema deve preservar:

- tecnicos usados
- percentual total usado
- valor total da comissao
- valor individual de cada tecnico
- valor da empresa

Campos relevantes em `movimentos`:

- `grupo_servico`
- `papel_servico`
- `tecnico`
- `divisao_tecnicos`
- `percentual_comissao_tecnico`
- `valor_comissao_tecnico`
- `valor_empresa`

### 6.1 Entrada do servico

Na entrada principal:

- `tipo = entrada`
- `papel_servico = entrada_servico`
- `percentual_comissao_tecnico = percentual total`
- `valor_comissao_tecnico = comissao total`
- `valor_empresa = valor liquido da empresa`

### 6.2 Saidas de comissao

Nas saidas:

- `tipo = saida`
- `papel_servico = comissao_tecnica`
- cada tecnico pode receber sua propria saida
- cada saida guarda percentual e valor individual

## 7. Interface do Novo registro

No modo `servico tecnico`, a tela deve:

- esconder `Categoria` como campo manual
- mostrar selecao de tecnicos
- mostrar tecnicos selecionados em chips compactos
- mostrar resumo visual de:
  - comissao total
  - valor da empresa
  - divisao da comissao

Textos da interface devem permanecer legiveis em portugues:

- `Servico tecnico`
- `Tecnicos responsaveis`
- `Comissao total`
- `Divisao da comissao`
- `Valor da empresa`

O campo de percentual de comissao do tecnico usa a mesma mascara numerica `MoneyMaskEntry`, exibindo no padrao `0,00`. Exemplos validos: `10`, `10,00` e `10.00`. O servico normaliza o valor para percentual `float` e continua validando a faixa entre `0` e `100`.

## 8. Historico, consultas e exportacoes

O sistema deve continuar funcionando com:

- historico
- registros
- consultas e filtros
- exportacao Excel
- exportacao PDF

Quando houver varios tecnicos:

- a leitura deve mostrar os nomes combinados quando necessario
- a exportacao nao pode quebrar
- a divisao interna deve continuar disponivel para leitura futura

## 9. Compatibilidade retroativa

Regras obrigatorias:

- nao migrar registros antigos automaticamente
- registros antigos sem tecnico continuam validos
- servicos antigos com um tecnico continuam validos
- registros antigos com categoria `Comissao` continuam validos
- dados antigos nao podem quebrar dashboard, historico ou exportacao

Quando o sistema precisar tratar um servico antigo com um tecnico:

- pode considerar internamente como lista com um unico tecnico

## 10. Checklist ao mexer nesse fluxo

- testar servico tecnico com um tecnico
- testar servico tecnico com dois tecnicos
- testar soma total abaixo de `100%`
- testar soma total igual a `100%`
- testar bloqueio acima de `100%`
- confirmar que o valor da empresa nao gera nova movimentacao
- confirmar que o dashboard mostra o lucro correto
- confirmar que o historico continua legivel
- confirmar que exportacao Excel e PDF continuam abrindo

## 11. Regra de ouro

Se houver qualquer duvida ao alterar esse fluxo, preservar sempre:

- compatibilidade com dados antigos
- uma leitura financeira coerente
- ausencia de duplicacao de lucro
