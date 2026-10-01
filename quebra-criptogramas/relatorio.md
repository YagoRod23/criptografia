# Relatório: quebra de criptogramas (substituição monoalfabética e Vigenère)

**Disciplina:** Segurança da Informação, UFCA
**Arquivos de entrada:** `criptogramas2.txt` (71 criptogramas) e `dicionario2.txt` (428 palavras)
**Ferramenta desenvolvida:** `quebra_cifras.py` (Python 3, sem bibliotecas externas)
**Resultado:** os **71 criptogramas foram quebrados** (58 monoalfabéticos e 13 Vigenère). As respostas completas estão em `respostas.txt` e no Anexo.

---

## 1. Visão geral

Os criptogramas não têm espaços nem pontuação e usam só as letras A–Z. O enunciado traz duas informações que orientaram a estratégia:

1. **Quais criptogramas são Vigenère:** 7, 11, 17, 22, 27, 33, 37, 44, 47, 55, 57, 66 e 67. Os outros 58 usam substituição monoalfabética.
2. **Seis pares com o mesmo texto claro**, cifrados primeiro com a monoalfabética e depois com Vigenère: (10, 11), (21, 22), (32, 33), (43, 44), (54, 55) e (65, 66).

Com isso, a quebra seguiu quatro estratégias, todas implementadas em um único script:

| Estratégia | Usada em | Qtd. |
|---|---|---|
| Busca com dicionário (monoalfabética) | todos os monoalfabéticos | 58 |
| Vigenère pelos pares (texto claro conhecido) | 11, 22, 33, 44, 55, 66 | 6 |
| Vigenère por IC + análise de frequência (com refinamento) | 7, 27, 37, 47, 57, 67 | 6 |
| Vigenère por busca com dicionário | 17 | 1 |

O índice de coincidência (IC) também confirma a divisão do enunciado. O IC médio dos monoalfabéticos é **0,076**, próximo do português (≈ 0,078), porque a substituição monoalfabética preserva a distribuição de frequências. O IC médio dos Vigenère é **0,048**, mais perto de um texto aleatório (≈ 0,038), porque a cifra polialfabética espalha as frequências.

---

## 2. Substituição monoalfabética

### 2.1 Por que a análise de frequência pura não basta

Na substituição monoalfabética, cada letra do texto claro é sempre trocada pela mesma letra cifrada. O ataque clássico é a **análise de frequência**: a letra mais comum na cifra deve ser A, E ou O. Mas os criptogramas são curtos (10 a 290 letras), e em textos curtos as frequências variam muito. Usada sozinha, a análise de frequência gera várias hipóteses erradas.

### 2.2 Estratégia adotada: busca com dicionário guiada pelo padrão de letras

A monoalfabética tem uma propriedade forte: **ela preserva o padrão de repetição das letras**. Por exemplo:

```
palavra   C O D I G O      padrão 0 1 2 3 4 1   (a 2ª e a 6ª letra são iguais)
cifra     E Q F I Y Q      padrão 0 1 2 3 4 1   -> compatível
```

Como o dicionário tem as palavras usadas, o algoritmo **monta o criptograma inteiro como uma sequência de palavras do dicionário**:

1. Na posição atual da cifra, testa cada palavra do dicionário (as mais longas primeiro).
2. A palavra só serve se o **padrão de letras** for igual ao do trecho cifrado correspondente.
3. A palavra também precisa ser **consistente com o mapeamento já montado**. O mapeamento é bijetivo: uma letra cifrada sempre vira a mesma letra clara, e duas letras cifradas diferentes nunca viram a mesma letra clara.
4. Se servir, o algoritmo avança para depois da palavra e repete. Se travar, volta e tenta a próxima palavra (*backtracking*).
5. Entre as soluções completas, fica com a que usa **menos palavras** (*branch and bound*). Isso evita leituras artificiais como "EM O EM OS…" quando existe "TESTES AUTOMATIZADOS".

**Exemplo (#1):** `EQFIYQDIZMQ` vira **CODIGO LIMPO**, com o mapa E→C, Q→O, F→D, I→I, Y→G, D→L, Z→M, M→P. O Q aparece três vezes na cifra e as três viram O, de acordo com o padrão de CODIGO e LIMPO.

Resultado: os 58 monoalfabéticos foram quebrados, e a cifra decifrada pelo mapa encontrado reproduz cada criptograma letra por letra.

### 2.3 Casos que exigiram atenção

- **#2 (ambiguidade real):** `LEGPPCXSKP` admite **ROMA ANTIGA** e **PELA ANTIGA**. ROMA e PELA têm o mesmo padrão de letras (4 letras diferentes) e as duas estão no dicionário, então a criptoanálise sozinha não decide. O script registra as duas, e a escolha de "ROMA ANTIGA" é semântica: "PELA ANTIGA" não forma frase e os textos tratam de história antiga. Essa escolha está documentada no script (`ESCOLHA_SEMANTICA`).
- **#26:** o texto decifrado é `UMBANCOSGUARDADADOSORGANIZADOS`, ou seja, **UM BANCOS GUARDA DADOS ORGANIZADOS**. O dicionário original continha BANCO, não BANCOS, e com ele o criptograma não tinha solução. A busca exaustiva provou que nenhuma combinação de palavras do dicionário original fechava. A solução apareceu ao procurar com um dicionário de português maior. Depois disso, o `dicionario2.txt` da pasta foi ajustado (BANCO → BANCOS) e o script passou a resolver o #26 diretamente. O mapeamento é bijetivo e consistente em todas as 30 letras. O "BANCOS" no singular "UM" indica um provável erro de concordância no texto original.
- **#61:** a parte final decifra como **…O CONTEXTO DO PROJETOS TRANSFORMA**. As letras estão corretas e o mapeamento é consistente. A estranheza gramatical está no próprio texto, provavelmente "do projeto se transforma" sem uma letra.
- **#1 e #52:** o script também registrou leituras alternativas com o mesmo número de palavras ("PODE GOVERNO" no #1; "FENOMENO SE" em vez de "FENOMENOS E" no #52). Elas foram descartadas por não formarem frase. No #52, as duas leituras usam exatamente as mesmas letras.
- **#64:** a busca atingiu o limite de tempo (90 s) antes de provar que a solução era a de menor número de palavras. A solução encontrada passou na verificação e forma frase coerente.

---

## 3. Cifra de Vigenère

Na Vigenère, cada letra é deslocada por uma letra da chave, que se repete ao longo do texto:

```
C[i] = (P[i] + K[i mod L]) mod 26        P[i] = (C[i] − K[i mod L]) mod 26
```

Como a mesma letra clara vira letras cifradas diferentes, a cifra é **polialfabética** e não preserva frequências nem padrões de repetição. A quebra precisa primeiro do tamanho da chave (L) e depois de cada letra dela.

### 3.1 Vigenère pelos pares (ataque com texto claro conhecido)

Nos seis pares, o criptograma monoalfabético já tinha sido quebrado na etapa anterior. Isso dá o **texto claro do criptograma Vigenère**, e basta subtrair:

```
K[i] = (C[i] − P[i]) mod 26
```

O resultado é o **fluxo da chave**: a chave repetida ao longo do texto. A chave é o **menor período** desse fluxo.

**Exemplo (32, 33):** o #32 decifra como "A PROGRAMACAO TRANSFORMA IDEIAS EM INSTRUCOES". Subtraído do #33, dá:

```
fluxo: UFCACCTUFCACCTUFCACCTUFCACCTUFCACCTUFCAC
período 7 -> chave UFCACCT
```

| Par | Chave | Observação |
|---|---|---|
| (10, 11) | `EVOLUISOFTWAR` | 13 letras para um texto de 14: é o próprio texto claro rotacionado ("EVOLUI" + "SOFTWAR") |
| (21, 22) | `MESOPOTAMIALAGASH` | Mesopotâmia + Lagash (cidade suméria) |
| (32, 33) | `UFCACCT` | UFCA + CCT |
| (43, 44) | `ABCCBA` | palíndromo |
| (54, 55) | `OSANTIGOSROMANOS` | o próprio início do texto claro |
| (65, 66) | `QWERTY` | primeira fileira do teclado |

Esse ataque é exato: a chave decifra o criptograma Vigenère e reproduz exatamente o texto claro do par.

**Correção durante o trabalho:** no par (10, 11) cheguei a supor uma Vigenère *autokey*, em que a chave continua com o próprio texto claro, porque o fluxo `EVOLUISOFTWARE` parece isso. Os outros cinco pares mostraram chaves periódicas comuns, e o (10, 11) também se explica como uma chave periódica de 13 letras. Todos os 13 criptogramas usam a Vigenère padrão.

### 3.2 Vigenère por índice de coincidência + análise de frequência

Para os Vigenère sem par:

**Passo 1, tamanho da chave pelo IC.** O IC é a probabilidade de duas letras sorteadas do texto serem iguais. Se o texto é dividido em L colunas (letras nas posições i, i+L, i+2L…) e L é o tamanho certo, cada coluna foi cifrada com **uma única letra da chave**, ou seja, é uma cifra de César. O IC de cada coluna sobe então para perto do português (0,078). O script calcula o IC médio das colunas para L = 1…20 e ordena os candidatos.

**Passo 2, cada letra da chave pela frequência.** Para cada coluna, testa os 26 deslocamentos e escolhe o que deixa a distribuição de letras mais parecida com a do português (teste **qui-quadrado** com a tabela de frequências do português).

**Passo 3, refinamento com o dicionário.** Colunas curtas (≈ 10 letras) às vezes erram uma letra da chave. O script troca uma letra da chave por vez e mantém a troca que mais aumenta a **cobertura do texto por palavras do dicionário**, repetindo até nenhuma troca melhorar (subida mais íngreme). A chave final é aceita só se o texto decifrado inteiro se divide em palavras do dicionário.

**Exemplo (#57, 137 letras):**

```
IC do criptograma:   0,041   (cara de Vigenère)
IC médio por L:      L=13 -> 0,078   L=9 -> 0,044   L=15 -> 0,044
chave por frequência: VIGENERECIFRK   (12 de 13 letras certas)
após refinamento:     VIGENERECIFRA
texto: A EDUCACAO MATEMATICA NAO ENVOLVE APENAS CALCULAR RESULTADOS MAS TAMBEM ...
```

**Exemplo (#47, 74 letras):** o IC aponta L = 8 (0,066). A frequência dá `SOFTHXRZ`, e o refinamento corrige para `SOFTWXRZ`: "OS MAPAS UTILIZAM SIMBOLOS PARA REPRESENTAR ELEMENTOS PRESENTES NO ESPACO GEOGRAFICO".

| # | Letras | L | Chave | Como saiu |
|---|---|---|---|---|
| 7 | 23 | 2 | `IA` | frequência direto |
| 27 | 40 | 5 | `CHAVE` | frequência direto |
| 37 | 66 | 4 | `QUAL` | frequência direto |
| 47 | 74 | 8 | `SOFTWXRZ` | frequência + refinamento |
| 57 | 137 | 13 | `VIGENERECIFRA` | frequência + refinamento |
| 67 | 66 | 4 | `URCA` | frequência + refinamento (o IC apontou L=8, que é URCA repetida; chave reduzida ao menor período) |

**Limitação observada:** o IC só identifica o tamanho da chave com clareza em textos longos (#47 e #57). Nos curtos, o L com maior IC costuma estar errado, porque cada coluna tem 2 ou 3 letras e o IC fica instável. Por isso o script testa os 5 melhores L do IC. O #7 tem IC de 0,087, que parece monoalfabético, porque a chave `IA` tem a letra A (deslocamento zero): metade do texto fica sem cifrar.

### 3.3 Vigenère por busca com dicionário

Quando IC + frequência não chega a um texto válido, o script usa a mesma ideia da monoalfabética, adaptada à Vigenère. Para cada L, monta o criptograma como sequência de palavras do dicionário, e **cada palavra testada fixa letras da chave** nas posições `i mod L`. A palavra só é aceita se não contradiz as letras da chave já fixadas por palavras anteriores.

**#17** (27 letras) foi resolvido assim: com L = 8 a chave é `AABBCCAA` e o texto é "TESTES AJUDAM A ENCONTRAR ERROS". Como o texto é curto, chaves mais longas também poderiam produzir o mesmo texto. A chave registrada é a menor que funciona.

---

## 4. A ferramenta (`quebra_cifras.py`)

```bash
python3 quebra_cifras.py              # quebra os 71 e gera respostas.txt (~15 min, 4 núcleos)
python3 quebra_cifras.py 26 47 57     # quebra só os indicados (gera respostas_parcial.txt)
```

Ordem de execução:

1. Quebra os monoalfabéticos em paralelo, incluindo os que fazem par com algum Vigenère.
2. Deriva as chaves dos 6 Vigenère pareados e confere que cada chave decifra o criptograma no texto do par.
3. Quebra os Vigenère restantes: IC + frequência + refinamento e, se necessário, busca com dicionário.
4. Grava `respostas.txt` com cifra, texto claro, mapa ou chave, método usado e leituras alternativas.

Principais funções:

| Função | O que faz |
|---|---|
| `padrao` | assinatura de repetição das letras (base da monoalfabética) |
| `busca_dicionario` | *backtracking* + *branch and bound* comum às duas cifras |
| `quebrar_mono` | restrição de padrão + mapeamento bijetivo |
| `chave_pelo_par` | fluxo da chave = cifra − claro; menor período |
| `indice_coincidencia`, `tamanhos_por_ic` | estimativa do tamanho da chave |
| `chave_por_frequencia` | qui-quadrado por coluna |
| `refinar_chave`, `cobertura` | correção da chave pela cobertura do dicionário |
| `quebrar_vig_dicionario` | busca com dicionário fixando letras da chave |

### Verificação

Todas as 71 respostas foram conferidas de forma independente:
- o texto claro só tem palavras do dicionário;
- a cifra de cada resposta é a mesma do arquivo;
- nos Vigenère, a chave decifra o criptograma exatamente;
- nos monoalfabéticos, o mapeamento é bijetivo;
- os 6 pares têm o mesmo texto claro.

**71 de 71 passaram.**

### Uso de IA

Como o enunciado permite, usamos uma IA generativa (Claude) para acelerar o desenvolvimento do script e a análise dos resultados. As decisões de estratégia, as escolhas semânticas (#2) e as observações sobre o texto (#26, #61) estão documentadas acima para revisão do grupo.

---

## Anexo: as 71 respostas

| # | Cifra | Chave | Texto claro |
|---|---|---|---|
| 1 | Monoalfabética | — | CODIGO LIMPO |
| 2 | Monoalfabética | — | ROMA ANTIGA |
| 3 | Monoalfabética | — | DADOS ORGANIZADOS |
| 4 | Monoalfabética | — | A TERRA GIRA |
| 5 | Monoalfabética | — | TESTES AUTOMATIZADOS |
| 6 | Monoalfabética | — | CIENCIA AVANCA |
| 7 | Vigenère | `IA` | MAPAS REPRESENTAM LUGARES |
| 8 | Monoalfabética | — | NUMEROS REPRESENTAM QUANTIDADES |
| 9 | Monoalfabética | — | EGITO ANTIGO |
| 10 | Monoalfabética | — | SOFTWARE EVOLUI |
| 11 | Vigenère | `EVOLUISOFTWAR` | SOFTWARE EVOLUI |
| 12 | Monoalfabética | — | ALGORITMOS RESOLVEM PROBLEMAS |
| 13 | Monoalfabética | — | EDUCACAO TRANSFORMA VIDAS |
| 14 | Monoalfabética | — | FUNCOES RELACIONAM VALORES |
| 15 | Monoalfabética | — | COMPUTADORES PROCESSAM DADOS |
| 16 | Monoalfabética | — | HIPOTESES SAO TESTADAS |
| 17 | Vigenère | `AABBCCAA` | TESTES AJUDAM A ENCONTRAR ERROS |
| 18 | Monoalfabética | — | OS ROMANOS CONSTRUIRAM MUITAS ESTRADAS |
| 19 | Monoalfabética | — | A MATEMATICA ESTUDA PADROES E RELACOES |
| 20 | Monoalfabética | — | PROGRAMAS SEGUEM INSTRUCOES BEM DEFINIDAS |
| 21 | Monoalfabética | — | A LATITUDE INDICA POSICOES NORTESUL |
| 22 | Vigenère | `MESOPOTAMIALAGASH` | A LATITUDE INDICA POSICOES NORTESUL |
| 23 | Monoalfabética | — | A CIENCIA BUSCA EXPLICAR FENOMENOS |
| 24 | Monoalfabética | — | OS EGIPCIOS USAVAM ESCRITA HIEROGLIFICA |
| 25 | Monoalfabética | — | MAPAS MOSTRAM DIFERENTES PARTES DA TERRA |
| 26 | Monoalfabética | — | UM BANCOS GUARDA DADOS ORGANIZADOS |
| 27 | Vigenère | `CHAVE` | REQUISITOS DESCREVEM NECESSIDADES DO SISTEMA |
| 28 | Monoalfabética | — | A EDUCACAO DESENVOLVE NOVOS CONHECIMENTOS |
| 29 | Monoalfabética | — | ALGORITMOS ORGANIZAM PASSOS PARA RESOLVER PROBLEMAS |
| 30 | Monoalfabética | — | A LONGITUDE INDICA POSICOES LESTEOESTE |
| 31 | Monoalfabética | — | COMPUTADORES ARMAZENAM E PROCESSAM INFORMACOES |
| 32 | Monoalfabética | — | A PROGRAMACAO TRANSFORMA IDEIAS EM INSTRUCOES |
| 33 | Vigenère | `UFCACCT` | A PROGRAMACAO TRANSFORMA IDEIAS EM INSTRUCOES |
| 34 | Monoalfabética | — | A ENGENHARIA DE SOFTWARE CRIA METODOS PARA DESENVOLVER TESTAR E MANTER SISTEMAS DE COMPUTADOR |
| 35 | Monoalfabética | — | UM ALGORITMO APRESENTA PASSOS ORDENADOS PARA RESOLVER UM PROBLEMA DE MANEIRA ORGANIZADA |
| 36 | Monoalfabética | — | A MATEMATICA AJUDA A REPRESENTAR PROBLEMAS ENCONTRADOS NA COMPUTACAO E NA CIENCIA |
| 37 | Vigenère | `QUAL` | A CIENCIA UTILIZA OBSERVACOES EXPERIMENTOS PARA ESTUDAR FENOMENOS NATURAIS |
| 38 | Monoalfabética | — | A TERRA POSSUI DIFERENTES FORMAS DE RELEVO COMO MONTANHAS PLANICIES E PLANALTOS |
| 39 | Monoalfabética | — | OS ANTIGOS EGIPCIOS CONSTRUIRAM GRANDES MONUMENTOS PROXIMOS AO RIO NILO |
| 40 | Monoalfabética | — | A EDUCACAO PODE DESENVOLVER CONHECIMENTOS HABILIDADES E CAPACIDADE DE RESOLVER PROBLEMAS |
| 41 | Monoalfabética | — | UM PROGRAMA COMPUTADOR EXECUTA INSTRUCOES DEFINIDAS POR SEUS DESENVOLVEDORES |
| 42 | Monoalfabética | — | OS ROMANOS UTILIZARAM ESTRADAS PARA FACILITAR VIAGENS COMERCIO E COMUNICACAO |
| 43 | Monoalfabética | — | UMA FUNCAO MATEMATICA RELACIONA VALORES DE ENTRADA COM VALORES DE SAIDA |
| 44 | Vigenère | `ABCCBA` | UMA FUNCAO MATEMATICA RELACIONA VALORES DE ENTRADA COM VALORES DE SAIDA |
| 45 | Monoalfabética | — | OS TESTES DE SOFTWARE VERIFICAM SE UM SISTEMA APRESENTA O COMPORTAMENTO ESPERADO |
| 46 | Monoalfabética | — | A CIENCIA DEPENDE DE PERGUNTAS EVIDENCIAS E METODOS PARA PRODUZIR CONHECIMENTO |
| 47 | Vigenère | `SOFTWXRZ` | OS MAPAS UTILIZAM SIMBOLOS PARA REPRESENTAR ELEMENTOS PRESENTES NO ESPACO GEOGRAFICO |
| 48 | Monoalfabética | — | A ESCRITA PERMITIU REGISTRAR INFORMACOES E TRANSMITIR CONHECIMENTOS ENTRE DIFERENTES GERACOES |
| 49 | Monoalfabética | — | A APRENDIZAGEM MELHORA QUANDO O ESTUDANTE RELACIONA IDEIAS NOVAS COM CONHECIMENTOS ANTERIORES |
| 50 | Monoalfabética | — | A ENGENHARIA DE SOFTWARE UTILIZA PROCESSOS TECNICAS E FERRAMENTAS PARA CRIAR SISTEMAS CONFIAVEIS ORGANIZAR O TRABALHO DAS EQUIPES E FACILITAR MUDANCAS DURANTE A VIDA UTIL DO SOFTWARE |
| 51 | Monoalfabética | — | NA MATEMATICA UMA EQUACAO PODE REPRESENTAR UMA RELACAO ENTRE DIFERENTES QUANTIDADES E AJUDAR A ENCONTRAR VALORES DESCONHECIDOS |
| 52 | Monoalfabética | — | OS CIENTISTAS FORMULAM HIPOTESES PARA EXPLICAR FENOMENOS E REALIZAM EXPERIMENTOS OU OBSERVACOES PARA VERIFICAR SE ESSAS EXPLICACOES SAO COMPATIVEIS COM AS EVIDENCIAS ENCONTRADAS |
| 53 | Monoalfabética | — | A LOCALIZACAO DE UMA CIDADE PODE SER INDICADA POR LATITUDE E LONGITUDE PERMITINDO IDENTIFICAR SUA POSICAO NA SUPERFICIE TERRESTRE DE MANEIRA PRECISA |
| 54 | Monoalfabética | — | OS ANTIGOS ROMANOS DESENVOLVERAM SISTEMAS DE ESTRADAS LEIS E ADMINISTRACAO QUE AJUDARAM A ORGANIZAR UM GRANDE TERRITORIO DURANTE MUITOS SECULOS |
| 55 | Vigenère | `OSANTIGOSROMANOS` | OS ANTIGOS ROMANOS DESENVOLVERAM SISTEMAS DE ESTRADAS LEIS E ADMINISTRACAO QUE AJUDARAM A ORGANIZAR UM GRANDE TERRITORIO DURANTE MUITOS SECULOS |
| 56 | Monoalfabética | — | UM SISTEMA DE CONTROLE DE VERSOES REGISTRA ALTERACOES NO CODIGO E PERMITE QUE DIFERENTES PESSOAS TRABALHEM NO MESMO PROJETO COM MAIS SEGURANCA |
| 57 | Vigenère | `VIGENERECIFRA` | A EDUCACAO MATEMATICA NAO ENVOLVE APENAS CALCULAR RESULTADOS MAS TAMBEM COMPREENDER PROBLEMAS ESCOLHER ESTRATEGIAS E EXPLICAR COMO UMA SOLUCAO FOI ENCONTRADA |
| 58 | Monoalfabética | — | OS RIOS INFLUENCIAM A OCUPACAO HUMANA PORQUE FORNECEM AGUA FAVORECEM ATIVIDADES ECONOMICAS E PODEM FACILITAR O TRANSPORTE ENTRE DIFERENTES REGIOES |
| 59 | Monoalfabética | — | A DECOMPOSICAO DE UM PROBLEMA EM PARTES MENORES PODE FACILITAR SUA SOLUCAO TANTO EM ALGORITMOS QUANTO EM PROJETOS DE ENGENHARIA DE SOFTWARE |
| 60 | Monoalfabética | — | O ESTUDO DA HISTORIA ANTIGA PERMITE COMPREENDER COMO DIFERENTES SOCIEDADES ORGANIZARAM CIDADES GOVERNOS RELIGIOES ATIVIDADES ECONOMICAS E FORMAS DE REGISTRAR INFORMACOES |
| 61 | Monoalfabética | — | DURANTE O DESENVOLVIMENTO DE UM SISTEMA OS REQUISITOS PODEM MUDAR PORQUE OS USUARIOS DESCOBREM NOVAS NECESSIDADES OU PORQUE O CONTEXTO DO PROJETOS TRANSFORMA |
| 62 | Monoalfabética | — | NA MATEMATICA UM MODELO PODE REPRESENTAR UMA SITUACAO REAL USANDO NUMEROS FUNCOES EQUACOES OU GRAFICOS |
| 63 | Monoalfabética | — | A CIENCIA PROCURA COMPREENDER O MUNDO POR MEIO DE METODOS ORGANIZADOS DE INVESTIGACAO |
| 64 | Monoalfabética | — | A DISTRIBUICAO DAS CIDADES PELO TERRITORIO ESTA RELACIONADA A VARIOS FATORES GEOGRAFICOS |
| 65 | Monoalfabética | — | AS SOCIEDADES DO EGITO E DA MESOPOTAMIA DESENVOLVERAM FORMAS DE ESCRITA AGRICULTURA ORGANIZADA SISTEMAS DE GOVERNO E GRANDES CONSTRUCOES |
| 66 | Vigenère | `QWERTY` | AS SOCIEDADES DO EGITO E DA MESOPOTAMIA DESENVOLVERAM FORMAS DE ESCRITA AGRICULTURA ORGANIZADA SISTEMAS DE GOVERNO E GRANDES CONSTRUCOES |
| 67 | Vigenère | `URCA` | UM COMPUTADOR EXECUTA PROGRAMAS SEGUINDO INSTRUCOES ARMAZENADAS NA MEMORIA |
| 68 | Monoalfabética | — | NA EDUCACAO UMA ATIVIDADE PODE SER MAIS UTIL QUANDO EXIGE QUE O ESTUDANTE APLIQUE O CONHECIMENTO EM UMA SITUACAO CONCRETA |
| 69 | Monoalfabética | — | UM TESTE DE SOFTWARE NAO SERVE APENAS PARA ENCONTRAR ERROS DEPOIS QUE O PROGRAMA ESTA PRONTO |
| 70 | Monoalfabética | — | A POSICAO DE UM LUGAR NA TERRA PODE SER REPRESENTADA POR COORDENADAS GEOGRAFICAS |
| 71 | Monoalfabética | — | OS GREGOS ANTIGOS CONTRIBUIRAM PARA AREAS COMO MATEMATICA FILOSOFIA ASTRONOMIA E POLITICA ALGUMAS IDEIAS DESENVOLVIDAS NESSE PERIODO FORAM POSTERIORMENTE ESTUDADAS E MODIFICADAS POR OUTRAS SOCIEDADES CONHECER ESSE PROCESSO AJUDA A PERCEBER QUE O CONHECIMENTO E CONSTRUIDO AO LONGO DO TEMPO E RECEBE CONTRIBUICOES DE DIFERENTES CULTURAS |
