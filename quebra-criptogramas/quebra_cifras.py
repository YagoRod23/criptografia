"""
Quebra dos criptogramas da atividade (substituição monoalfabética e Vigenère).

Uso:
    python3 quebra_cifras.py              # quebra os 71 e gera respostas.txt
    python3 quebra_cifras.py 26 47 57     # quebra só os criptogramas indicados

Estratégias:
  1. Monoalfabética  -> busca com dicionário: o texto (sem espaços) é montado como
                        uma sequência de palavras do dicionário com o mesmo padrão
                        de letras repetidas, mantendo um mapeamento cifra<->claro
                        consistente (bijetivo). Escolhe a solução com menos palavras.
  2. Vigenère (pares) -> o texto claro do criptograma monoalfabético do par é
                        subtraído do criptograma Vigenère, revelando o fluxo da
                        chave; o menor período desse fluxo é a chave.
  3. Vigenère (IC)   -> índice de coincidência estima o tamanho da chave e a
                        análise de frequência (qui-quadrado) estima cada letra;
                        letras erradas são corrigidas maximizando a cobertura do
                        texto por palavras do dicionário.
  4. Vigenère (dic.) -> se a chave por frequência não gera texto válido, busca com
                        dicionário: cada palavra testada fixa letras da chave nas
                        posições i mod L, que não podem se contradizer.
"""

import math
import sys
import time
from collections import Counter
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ARQ_CRIPTOGRAMAS = PASTA / "criptogramas2.txt"
ARQ_DICIONARIO = PASTA / "dicionario2.txt"
ARQ_RESPOSTAS = PASTA / "respostas.txt"

# Informações dadas no enunciado
VIGENERE = {7, 11, 17, 22, 27, 33, 37, 44, 47, 55, 57, 66, 67}
PARES = [(10, 11), (21, 22), (32, 33), (43, 44), (54, 55), (65, 66)]  # (mono, vigenère)

# Frequência das letras em português (%)
FREQ_PT = {
    "A": 14.63, "B": 1.04, "C": 3.88, "D": 4.99, "E": 12.57, "F": 1.02, "G": 1.30,
    "H": 1.28, "I": 6.18, "J": 0.40, "K": 0.02, "L": 2.78, "M": 4.74, "N": 5.05,
    "O": 10.73, "P": 2.52, "Q": 1.20, "R": 6.53, "S": 7.81, "T": 4.34, "U": 4.63,
    "V": 1.67, "W": 0.01, "X": 0.21, "Y": 0.01, "Z": 0.47,
}

TEMPO_MONO = 90       # segundos por criptograma na busca monoalfabética
TEMPO_VIG_L = 60      # segundos por tamanho de chave na busca Vigenère
MAX_CHAVE = 20
MAX_EMPATES = 5     # leituras alternativas guardadas por criptograma

# Quando a criptoanálise deixa leituras empatadas (mesmo padrão de letras, mesmo nº de
# palavras), a escolha final é semântica. Só é aplicada se a frase estiver entre as
# soluções válidas encontradas pelo script.
ESCOLHA_SEMANTICA = {
    2: "ROMA ANTIGA",  # 'PELA ANTIGA' tem o mesmo padrão, mas não forma frase
}


# ---------------------------------------------------------------- leitura

def ler_criptogramas():
    linhas = ARQ_CRIPTOGRAMAS.read_text().splitlines()
    cripto = {}
    for i, linha in enumerate(linhas):
        if linha.startswith("Criptograma #"):
            num = int(linha.split("#")[1].split(",")[0])
            cripto[num] = linhas[i + 1].strip()
    return cripto


def ler_dicionario():
    palavras = {p.strip().upper() for p in ARQ_DICIONARIO.read_text().splitlines() if p.strip()}
    # longas primeiro (acha boas soluções cedo); desempate alfabético para resultado determinístico
    return sorted(palavras, key=lambda p: (-len(p), p))


PALAVRAS = ler_dicionario()
CONJ_PALAVRAS = set(PALAVRAS)
MAX_PALAVRA = max(map(len, PALAVRAS))


def padrao(s):
    """'ABCA' -> (0,1,2,0): formato de repetição das letras."""
    vistos = {}
    return tuple(vistos.setdefault(ch, len(vistos)) for ch in s)


PADRAO = {p: padrao(p) for p in PALAVRAS}


# ---------------------------------------------------------------- utilitários

def deslocar(c, k, sinal):
    return chr((ord(c) - 65 + sinal * (ord(k) - 65)) % 26 + 65)


def vig_decifrar(texto, chave):
    return "".join(deslocar(c, chave[i % len(chave)], -1) for i, c in enumerate(texto))


def menor_periodo(s):
    return next(L for L in range(1, len(s) + 1) if all(s[i] == s[i % L] for i in range(len(s))))


def segmentar(texto):
    """Divide o texto em palavras do dicionário (menor número de palavras) ou None."""
    @lru_cache(None)
    def f(i):
        if i == len(texto):
            return ()
        melhor = None
        for j in range(min(len(texto), i + MAX_PALAVRA), i, -1):
            if texto[i:j] in CONJ_PALAVRAS:
                resto = f(j)
                if resto is not None and (melhor is None or len(resto) + 1 < len(melhor)):
                    melhor = (texto[i:j],) + resto
        return melhor
    r = f(0)
    return list(r) if r is not None else None


class TempoEsgotado(Exception):
    pass


def busca_dicionario(cifra, encaixa, tempo_max):
    """
    Branch & bound: monta a cifra como sequência de palavras do dicionário,
    minimizando o número de palavras. Também guarda até MAX_EMPATES outras
    soluções com o mesmo número de palavras (leituras ambíguas). `encaixa(i, palavra)` aplica as restrições
    da cifra e devolve uma função para desfazer, ou None se a palavra não serve.
    """
    n = len(cifra)
    melhor = [math.inf, None]
    empates = []
    atual = []
    inicio = time.time()

    def rec(i):
        if time.time() - inicio > tempo_max:
            raise TempoEsgotado
        if i == n:
            if len(atual) < melhor[0]:
                melhor[:] = [len(atual), list(atual)]
                empates.clear()
            elif len(atual) == melhor[0] and len(empates) < MAX_EMPATES:
                empates.append(list(atual))
            return
        limite = len(atual) + math.ceil((n - i) / MAX_PALAVRA)
        if limite > melhor[0] or (limite == melhor[0] and len(empates) >= MAX_EMPATES):
            return  # não tem como ficar melhor que a solução já achada
        for p in PALAVRAS:
            if i + len(p) > n:
                continue
            desfazer = encaixa(i, p)
            if desfazer is None:
                continue
            atual.append(p)
            rec(i + len(p))
            atual.pop()
            desfazer()

    esgotou = False
    try:
        rec(0)
    except TempoEsgotado:
        esgotou = True
    return melhor[1], empates, esgotou


# ---------------------------------------------------------------- monoalfabética

def quebrar_mono(cifra, tempo_max=TEMPO_MONO):
    cif_para_claro, claro_para_cif = {}, {}

    def encaixa(i, p):
        trecho = cifra[i:i + len(p)]
        if PADRAO[p] != padrao(trecho):
            return None
        novos = []
        for c, l in zip(trecho, p):
            if c in cif_para_claro:
                if cif_para_claro[c] != l:
                    break
            elif l in claro_para_cif:
                break
            else:
                cif_para_claro[c] = l
                claro_para_cif[l] = c
                novos.append(c)
        else:
            def desfazer():
                for c in novos:
                    del claro_para_cif[cif_para_claro.pop(c)]
            return desfazer
        for c in novos:
            del claro_para_cif[cif_para_claro.pop(c)]
        return None

    palavras, empates, esgotou = busca_dicionario(cifra, encaixa, tempo_max)
    if not palavras:
        return None
    claro = "".join(palavras)
    mapa = dict(sorted(zip(cifra, claro)))
    return {"palavras": palavras, "mapa": mapa, "parcial": esgotou, "alternativas": empates}


# ---------------------------------------------------------------- Vigenère

def indice_coincidencia(s):
    n = len(s)
    if n < 2:
        return 0.0
    return sum(v * (v - 1) for v in Counter(s).values()) / (n * (n - 1))


def tamanhos_por_ic(cifra, max_l=MAX_CHAVE):
    """Tamanhos de chave ordenados pelo IC médio das colunas (maior = mais provável)."""
    notas = []
    for L in range(1, min(max_l, len(cifra) // 2) + 1):
        colunas = [cifra[i::L] for i in range(L)]
        notas.append((sum(map(indice_coincidencia, colunas)) / L, L))
    return [L for _, L in sorted(notas, reverse=True)]


def letra_por_frequencia(coluna):
    """Letra da chave que minimiza o qui-quadrado entre a coluna decifrada e o português."""
    n = len(coluna)
    def qui2(k):
        cont = Counter(deslocar(c, chr(k + 65), -1) for c in coluna)
        return sum((cont[l] - n * f / 100) ** 2 / (n * f / 100) for l, f in FREQ_PT.items())
    return chr(min(range(26), key=qui2) + 65)


def chave_por_frequencia(cifra, L):
    return "".join(letra_por_frequencia(cifra[i::L]) for i in range(L))


def cobertura(texto):
    """Pontua o quanto o texto é formado por palavras do dicionário (soma de len² das palavras)."""
    melhor = [0] * (len(texto) + 1)
    for i in range(len(texto) - 1, -1, -1):
        melhor[i] = melhor[i + 1]  # letra não coberta
        for j in range(i + 2, min(len(texto), i + MAX_PALAVRA) + 1):
            if texto[i:j] in CONJ_PALAVRAS:
                melhor[i] = max(melhor[i], (j - i) ** 2 + melhor[j])
    return melhor[0]


def refinar_chave(cifra, chave):
    """
    A frequência acerta a maioria das letras da chave, mas erra algumas em colunas curtas.
    A cada rodada testa todas as trocas de uma letra e aplica só a que mais aumenta a
    cobertura do dicionário (subida mais íngreme), até nenhuma troca melhorar.
    """
    chave = list(chave)
    nota = cobertura(vig_decifrar(cifra, chave))
    while True:
        melhor_nota, melhor_chave = nota, None
        for pos in range(len(chave)):
            for letra in map(chr, range(65, 91)):
                teste = chave[:pos] + [letra] + chave[pos + 1:]
                n = cobertura(vig_decifrar(cifra, teste))
                if n > melhor_nota:
                    melhor_nota, melhor_chave = n, teste
        if melhor_chave is None:
            return "".join(chave)
        chave, nota = melhor_chave, melhor_nota


def quebrar_vig_dicionario(cifra, L, tempo_max=TEMPO_VIG_L):
    chave = [None] * L

    def encaixa(i, p):
        fixadas = []
        for j, l in enumerate(p):
            k = (ord(cifra[i + j]) - ord(l)) % 26
            pos = (i + j) % L
            if chave[pos] is None:
                chave[pos] = k
                fixadas.append(pos)
            elif chave[pos] != k:
                break
        else:
            def desfazer():
                for pos in fixadas:
                    chave[pos] = None
            return desfazer
        for pos in fixadas:
            chave[pos] = None
        return None

    palavras, empates, esgotou = busca_dicionario(cifra, encaixa, tempo_max)
    if not palavras:
        return None
    claro = "".join(palavras)
    fluxo = "".join(chr((ord(c) - ord(p)) % 26 + 65) for c, p in zip(cifra, claro))
    return {"palavras": palavras, "chave": fluxo[:L], "parcial": esgotou}


def quebrar_vig_sozinho(cifra):
    """Vigenère sem par; a chave final é reduzida ao menor período (URCAURCA -> URCA)."""
    r = _quebrar_vig_sozinho(cifra)
    if r:
        fluxo = "".join(r["chave"][i % len(r["chave"])] for i in range(len(cifra)))
        r["chave"] = fluxo[:menor_periodo(fluxo)]
    return r


def _quebrar_vig_sozinho(cifra):
    """Vigenère sem par: IC + frequência (+ refinamento); se falhar, busca com dicionário."""
    tamanhos = tamanhos_por_ic(cifra)
    for L in tamanhos[:5]:
        chave = chave_por_frequencia(cifra, L)
        palavras = segmentar(vig_decifrar(cifra, chave))
        if palavras:
            return {"palavras": palavras, "chave": chave, "metodo": f"IC (L={L}) + análise de frequência"}
        refinada = refinar_chave(cifra, chave)
        palavras = segmentar(vig_decifrar(cifra, refinada))
        if palavras:
            return {"palavras": palavras, "chave": refinada,
                    "metodo": f"IC (L={L}) + análise de frequência (chave estimada {chave}) "
                              f"+ refinamento por cobertura do dicionário"}
    # a ordem do IC também guia a busca por dicionário; todos os L são testados
    for L in sorted(range(1, min(MAX_CHAVE, len(cifra) // 2) + 1), key=tamanhos.index):
        r = quebrar_vig_dicionario(cifra, L)
        if r:
            r["metodo"] = f"busca com dicionário (L={L}, ordem sugerida pelo IC)"
            return r
    return None


def chave_pelo_par(cifra_vig, claro):
    fluxo = "".join(chr((ord(c) - ord(p)) % 26 + 65) for c, p in zip(cifra_vig, claro))
    return fluxo[:menor_periodo(fluxo)], fluxo


# ---------------------------------------------------------------- orquestração

def resolver_mono(item):
    num, cifra = item
    r = quebrar_mono(cifra)
    return num, r


def resolver_vig(item):
    num, cifra = item
    return num, quebrar_vig_sozinho(cifra)


def main():
    cripto = ler_criptogramas()
    alvo = {int(a) for a in sys.argv[1:]} or set(cripto)
    respostas = {}

    # 1) monoalfabéticos (inclui os do par, necessários para os Vigenère pareados)
    par_mono = {m for m, v in PARES if v in alvo}
    monos = sorted((n, cripto[n]) for n in cripto if n not in VIGENERE and (n in alvo or n in par_mono))
    with Pool() as pool:
        for num, r in pool.imap_unordered(resolver_mono, monos):
            if r and num in ESCOLHA_SEMANTICA:
                escolhida = ESCOLHA_SEMANTICA[num].split()
                if escolhida in r["alternativas"]:
                    r["alternativas"] = [r["palavras"]] + [a for a in r["alternativas"] if a != escolhida]
                    r["palavras"] = escolhida
                    r["mapa"] = dict(sorted(zip(cripto[num], "".join(escolhida))))
            if r:
                metodo = "busca com dicionário (padrão de letras + mapeamento consistente)"
                if r["parcial"]:
                    metodo += " [tempo esgotado: melhor solução encontrada]"
                respostas[num] = {"cifra": "Monoalfabética", "palavras": r["palavras"],
                                  "mapa": r["mapa"], "metodo": metodo,
                                  "alternativas": r["alternativas"]}
            else:
                respostas[num] = {"cifra": "Monoalfabética", "palavras": None,
                                  "metodo": "sem solução só com palavras do dicionário"}
            print(f"#{num:2} mono: {' '.join(r['palavras']) if r else 'SEM SOLUÇÃO'}", flush=True)

    # 2) Vigenère pelos pares
    pareados = {}
    for m, v in PARES:
        if v in alvo and respostas.get(m, {}).get("palavras"):
            claro = "".join(respostas[m]["palavras"])
            chave, fluxo = chave_pelo_par(cripto[v], claro)
            assert vig_decifrar(cripto[v], chave) == claro
            pareados[v] = True
            respostas[v] = {"cifra": "Vigenère", "palavras": respostas[m]["palavras"], "chave": chave,
                            "metodo": f"par com o #{m}: fluxo da chave = cifra − claro = {fluxo}; "
                                      f"menor período = {len(chave)}"}
            print(f"#{v:2} vig (par #{m}): chave {chave}", flush=True)

    # 3) Vigenère sem par: IC + frequência, depois busca com dicionário
    sozinhos = sorted((n, cripto[n]) for n in VIGENERE & alvo if n not in pareados)
    with Pool() as pool:
        for num, r in pool.imap_unordered(resolver_vig, sozinhos):
            if r:
                respostas[num] = {"cifra": "Vigenère", "palavras": r["palavras"], "chave": r["chave"],
                                  "metodo": r["metodo"]}
            else:
                respostas[num] = {"cifra": "Vigenère", "palavras": None, "metodo": "sem solução"}
            print(f"#{num:2} vig: {r['chave'] + ' -> ' + ' '.join(r['palavras']) if r else 'SEM SOLUÇÃO'}",
                  flush=True)

    # 4) gravação
    saida = []
    for num in sorted(respostas):
        r = respostas[num]
        saida.append(f"Criptograma #{num}  [{r['cifra']}]")
        saida.append(f"  Cifrado: {cripto[num]}")
        saida.append(f"  Claro:   {' '.join(r['palavras']) if r['palavras'] else '(não resolvido)'}")
        for alt in r.get("alternativas", []):
            saida.append(f"  Ambíguo: {' '.join(alt)}  (mesmo nº de palavras, também válido)")
        if r.get("mapa"):
            saida.append("  Mapa:    " + " ".join(f"{c}->{l}" for c, l in r["mapa"].items()))
        if r.get("chave"):
            saida.append(f"  Chave:   {r['chave']}")
        saida.append(f"  Método:  {r['metodo']}")
        saida.append("")
    destino = ARQ_RESPOSTAS if alvo == set(cripto) else PASTA / "respostas_parcial.txt"
    destino.write_text("\n".join(saida))
    print(f"\nRespostas gravadas em {destino}")


if __name__ == "__main__":
    main()
