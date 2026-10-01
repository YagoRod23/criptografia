# Quebra de criptogramas: monoalfabética e Vigenère

Atividade de Segurança da Informação (UFCA): quebrar 71 criptogramas cifrados com
substituição monoalfabética ou Vigenère, com ajuda de um dicionário de palavras.

| Arquivo | Conteúdo |
|---|---|
| `quebra_cifras.py` | script de quebra (monoalfabética, Vigenère pelos pares, IC + frequência, busca com dicionário) |
| `respostas.txt` | as 71 respostas: texto claro, cifra, chave/mapa e método |
| `relatorio.md` | relatório explicando como cada cifra foi quebrada |
| `respostas_vigenere.csv` | resumo dos 13 criptogramas Vigenère |
| `criptogramas2.txt`, `dicionario2.txt` | arquivos de entrada da atividade |

```bash
python3 quebra_cifras.py            # quebra os 71 e gera respostas.txt (~15 min)
python3 quebra_cifras.py 26 47 57   # quebra só os indicados
```
