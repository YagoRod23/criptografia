from collections import Counter

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


def main():
    texto = input("Digite o texto cifrado: ").strip()

    contador, total = analisar_frequencia(texto)
    sugestoes = sugerir_letras(contador, total)

    print(f"\n{'Letra':<8}{'Qtd':<8}{'%':<10}{'Sugestões'}")
    print("-" * 45)

    for letra, quantidade in contador.most_common():
        porcentagem = (quantidade / total) * 100
        sugestao = ", ".join(sugestoes[letra])
        print(f"{letra:<8}{quantidade:<8}{porcentagem:<10.1f}{sugestao}")


if __name__ == "__main__":
    main()