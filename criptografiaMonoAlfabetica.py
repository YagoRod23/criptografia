import argparse
import csv
import math
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

# Frequência de letras no português (fonte: tabela padrão de análise de frequência)
FREQUENCIA_PT = {
    'a': 14.63, 'b': 1.04, 'c': 3.88, 'd': 4.99, 'e': 12.57,
    'f': 1.02, 'g': 1.30, 'h': 1.28, 'i': 6.18, 'j': 0.40,
    'k': 0.02, 'l': 2.78, 'm': 4.74, 'n': 5.05, 'o': 10.73,
    'p': 2.52, 'q': 1.20, 'r': 6.53, 's': 7.81, 't': 4.34,
    'u': 4.63, 'v': 1.67, 'w': 0.01, 'x': 0.21, 'y': 0.01, 'z': 0.47
}

# Ranking do português, do mais frequente para o menos frequente
RANKING_PT = sorted(FREQUENCIA_PT, key=FREQUENCIA_PT.get, reverse=True)

PASTA_ATIVIDADE = Path.home() / "Área de trabalho" / "SegurancaDaInformacao"
ARQ_DICIONARIO = PASTA_ATIVIDADE / "dicionario2.txt"

# Informações dadas no enunciado: o resto dos criptogramas é monoalfabético
CRIPTOGRAMAS_VIGENERE = {7, 11, 17, 22, 27, 33, 37, 44, 47, 55, 57, 66, 67}
PARES = {10: 11, 21: 22, 32: 33, 43: 44, 54: 55, 65: 66}  # monoalfabético -> vigenère

TEMPO_MAXIMO = 20      # segundos de busca no dicionário
MAX_SOLUCOES = 500     # soluções coletadas antes de parar a busca
N_EXIBIDAS = 10        # soluções mostradas ao usuário


def analisar_frequencia(texto):
    texto = texto.upper()
    letras = [c for c in texto if c.isalpha()]
    total = len(letras)
    contador = Counter(letras)
    return contador, total


def sugerir_letras(contador, total, n_sugestoes=3):
    """
    Ordena as letras do texto por frequência (maior pra menor) e associa
    cada posição do ranking à mesma posição no ranking do português,
    sugerindo as N letras mais próximas daquele "posto" de frequência.
    """
    mais_comuns = contador.most_common()
    sugestoes = {}

    for posicao, (letra, _) in enumerate(mais_comuns):
        candidatos = RANKING_PT[max(0, posicao - 1): posicao + n_sugestoes - 1]
        sugestoes[letra] = [c.upper() for c in candidatos]

    return sugestoes


# ---------------------------------------------------------------- dicionário

def padrao(palavra):
    """'CASA' -> (0, 1, 2, 1): formato de repetição das letras."""
    vistos = {}
    return tuple(vistos.setdefault(c, len(vistos)) for c in palavra)


def carregar_dicionario(caminho=ARQ_DICIONARIO):
    """Agrupa as palavras do dicionário pelo padrão de letras repetidas."""
    palavras = {p.strip().upper() for p in caminho.read_text().splitlines() if p.strip()}
    por_padrao = defaultdict(list)
    for p in palavras:
        por_padrao[padrao(p)].append(p)
    return por_padrao, max(map(len, palavras))


def afinidade(cifra, palavra, sugestoes_amplas):
    """Quantas letras da palavra batem com as sugestões da análise de frequência."""
    return sum(l in sugestoes_amplas.get(c, ()) for c, l in zip(cifra, palavra))


def pontuacao_estatistica(cifra, claro, contador, total):
    """
    Log-verossimilhança média do mapeamento: para cada letra cifrada, a frequência
    observada no criptograma pesa a probabilidade, em português, da letra clara
    associada a ela. Quanto mais perto de zero, mais o texto "parece" português.
    """
    mapa = dict(zip(cifra, claro))
    return sum(qtd * math.log(FREQUENCIA_PT[mapa[c].lower()] / 100)
               for c, qtd in contador.items()) / total


def buscar_solucoes(texto, contador, total, sugestoes, arq_dicionario=ARQ_DICIONARIO):
    """
    Monta o criptograma como uma sequência de palavras do dicionário. Cada palavra
    precisa ter o mesmo padrão de letras repetidas do trecho cifrado e o mapeamento
    cifra -> claro precisa continuar consistente (uma letra cifrada = uma letra clara).
    A análise de frequência define a ordem em que as palavras são testadas.
    Espaços no texto cifrado, se existirem, são tratados como fronteiras de palavra.
    """
    por_padrao, max_palavra = carregar_dicionario(arq_dicionario)

    cifra = "".join(c for c in texto.upper() if c.isalpha())
    fronteiras, pos = set(), 0
    for bloco in texto.upper().split():
        pos += sum(c.isalpha() for c in bloco)
        fronteiras.add(pos)
    n = len(cifra)

    def cabe(i, j):
        return not any(k in fronteiras for k in range(i + 1, j))

    # Sugestões mais amplas (5 letras por posição) só para ordenar a busca
    sugestoes_amplas = {c: set(s) for c, s in sugerir_letras(contador, total, 5).items()}

    # candidatos[i] = palavras que podem começar na posição i, das mais prováveis às menos
    candidatos = []
    for i in range(n):
        lista = []
        for j in range(i + 1, min(n, i + max_palavra) + 1):
            if cabe(i, j):
                trecho = cifra[i:j]
                lista += [(p, j) for p in por_padrao.get(padrao(trecho), ())]
        lista.sort(key=lambda pj: (afinidade(cifra[i:], pj[0], sugestoes_amplas), len(pj[0])),
                   reverse=True)
        candidatos.append(lista)

    # alcanca_fim[i]: existe alguma divisão em palavras de i até o fim (ignorando o mapeamento)
    alcanca_fim = [False] * n + [True]
    for i in range(n - 1, -1, -1):
        alcanca_fim[i] = any(alcanca_fim[j] for _, j in candidatos[i])

    solucoes = {}
    cif_para_claro, claro_para_cif = {}, {}
    atual = []
    inicio = time.time()

    def rec(i):
        if len(solucoes) >= MAX_SOLUCOES or time.time() - inicio > TEMPO_MAXIMO:
            return
        if i == n:
            claro = "".join(atual)
            if claro not in solucoes or len(atual) < len(solucoes[claro]):
                solucoes[claro] = list(atual)
            return
        for palavra, j in candidatos[i]:
            if not alcanca_fim[j]:
                continue
            novos = []
            ok = True
            for c, l in zip(cifra[i:j], palavra):
                if c in cif_para_claro:
                    ok = cif_para_claro[c] == l
                elif l in claro_para_cif:
                    ok = False
                else:
                    cif_para_claro[c] = l
                    claro_para_cif[l] = c
                    novos.append(c)
                if not ok:
                    break
            if ok:
                atual.append(palavra)
                rec(j)
                atual.pop()
            for c in novos:
                del claro_para_cif[cif_para_claro.pop(c)]

    rec(0)
    esgotou = time.time() - inicio > TEMPO_MAXIMO or len(solucoes) >= MAX_SOLUCOES

    # Ranking: menos palavras primeiro (frases com palavras longas são mais confiáveis),
    # desempate pela aderência às frequências do português
    ranking = sorted(
        ((palavras, pontuacao_estatistica(cifra, claro, contador, total))
         for claro, palavras in solucoes.items()),
        key=lambda ps: (len(ps[0]), -ps[1]),
    )
    return cifra, ranking, esgotou


# ---------------------------------------------------------------- atividade

def ler_criptogramas(pasta):
    linhas = (pasta / "criptogramas2.txt").read_text().splitlines()
    cripto = {}
    for i, linha in enumerate(linhas):
        if linha.startswith("Criptograma #"):
            num = int(linha.split("#")[1].split(",")[0])
            cripto[num] = linhas[i + 1].strip().upper()
    return cripto


def periodo_vigenere(cifra_vig, claro):
    """Menor período do fluxo de chave (cifra - claro) do Vigenère do par."""
    fluxo = [(ord(c) - ord(p)) % 26 for c, p in zip(cifra_vig, claro)]
    return next(L for L in range(1, len(fluxo) + 1)
                if all(fluxo[i] == fluxo[i % L] for i in range(len(fluxo))))


def chave_da_solucao(cifra, claro):
    """Alfabeto cifrado: para cada letra clara de A a Z, a letra cifrada (ou '-' se não aparece)."""
    claro_para_cif = dict(zip(claro, cifra))
    return "".join(claro_para_cif.get(l, "-") for l in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def resolver(item):
    num, cifra, cifra_par, pasta = item
    contador, total = analisar_frequencia(cifra)
    _, ranking, _ = buscar_solucoes(cifra, contador, total, sugerir_letras(contador, total),
                                    pasta / "dicionario2.txt")
    if not ranking:
        return num, None, 0
    melhor = ranking[0]
    if cifra_par:
        # o Vigenère do par tem o mesmo texto claro: a chave real se repete,
        # então vale a solução cujo fluxo de chave tem o menor período
        melhor = min(ranking, key=lambda ps: (periodo_vigenere(cifra_par, "".join(ps[0])),
                                              len(ps[0]), -ps[1]))
        empatadas = 1
    else:
        empatadas = sum(len(p) == len(melhor[0]) for p, _ in ranking)
    return num, melhor[0], empatadas


def quebrar_atividade(pasta=PASTA_ATIVIDADE):
    cripto = ler_criptogramas(pasta)
    itens = [(n, cripto[n], cripto.get(PARES.get(n)), pasta)
             for n in sorted(cripto) if n not in CRIPTOGRAMAS_VIGENERE]

    print(f"Quebrando {len(itens)} criptogramas monoalfabéticos...\n")
    resultados = {}
    with Pool() as pool:
        for num, palavras, empatadas in pool.imap_unordered(resolver, itens):
            resultados[num] = (palavras, empatadas)
            aviso = f"   [atenção: {empatadas} soluções com o mesmo nº de palavras]" if empatadas > 1 else ""
            print(f"#{num:<3} {' '.join(palavras) if palavras else 'SEM SOLUÇÃO'}{aviso}", flush=True)

    destino = pasta / "respostas_monoalfabetica.csv"
    with open(destino, "w", newline="", encoding="utf-8") as arq:
        saida = csv.writer(arq, delimiter=";")
        saida.writerow(["Texto criptografado", "Chave (A-Z claro -> cifra)", "Texto descriptografado"])
        for num, cifra, _, _ in itens:
            palavras, _ = resultados[num]
            if palavras:
                saida.writerow([cifra, chave_da_solucao(cifra, "".join(palavras)), " ".join(palavras)])
            else:
                saida.writerow([cifra, "?", "(não resolvido)"])

    ambiguos = sorted(n for n, (_, e) in resultados.items() if e > 1)
    if ambiguos:
        print(f"\nCriptogramas com mais de uma solução possível (confira): {ambiguos}")
    print(f"\nRespostas gravadas em {destino}")


def main():
    parser = argparse.ArgumentParser(description="Quebra de cifra monoalfabética.")
    parser.add_argument("-q", "--quebrar", action="store_true",
                        help="quebrar os monoalfabéticos de criptogramas2.txt e gerar respostas_monoalfabetica.csv")
    parser.add_argument("--pasta", type=Path, default=PASTA_ATIVIDADE,
                        help="pasta com criptogramas2.txt e dicionario2.txt")
    args = parser.parse_args()

    if args.quebrar:
        quebrar_atividade(args.pasta)
        return

    texto = input("Digite o texto cifrado: ").strip()

    contador, total = analisar_frequencia(texto)
    sugestoes = sugerir_letras(contador, total)

    print(f"\n{'Letra':<8}{'Qtd':<8}{'%':<10}{'Sugestões'}")
    print("-" * 45)

    for letra, quantidade in contador.most_common():
        porcentagem = (quantidade / total) * 100
        sugestao = ", ".join(sugestoes[letra])
        print(f"{letra:<8}{quantidade:<8}{porcentagem:<10.1f}{sugestao}")

    print(f"\nBuscando soluções no dicionário ({ARQ_DICIONARIO.name})...")
    cifra, ranking, esgotou = buscar_solucoes(texto, contador, total, sugestoes)

    if not ranking:
        print("Nenhuma solução formada só por palavras do dicionário.")
        return

    print(f"\n{len(ranking)} solução(ões) encontrada(s)"
          + (" (busca interrompida por tempo/limite)" if esgotou else "")
          + f". Mostrando até {N_EXIBIDAS}:\n")

    for pos, (palavras, nota) in enumerate(ranking[:N_EXIBIDAS], 1):
        mapa = dict(sorted(zip(cifra, "".join(palavras))))
        print(f"{pos:>2}. {' '.join(palavras)}")
        print(f"    palavras: {len(palavras)}  |  pontuação estatística: {nota:.3f}")
        print(f"    mapa: {' '.join(f'{c}->{l}' for c, l in mapa.items())}\n")


if __name__ == "__main__":
    main()
