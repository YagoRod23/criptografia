def cifra_cesar(texto, deslocamento):
    resultado = ""
    for letra in texto:
        if letra.isalpha():
            base = ord('A') if letra.isupper() else ord('a')
            resultado += chr((ord(letra) - base + deslocamento) % 26 + base)
        else:
            resultado += letra 
    return resultado


texto = input("Digite o texto a ser analisado: ").strip().upper()

print("\nTestando todos os deslocamentos possíveis:\n")
for deslocamento in range(26):
    print(f"{deslocamento:2d}: {cifra_cesar(texto, deslocamento)}")