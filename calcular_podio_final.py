import os
import django

# 1. Inicializa o ambiente do Django nativamente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from bolao.models import Partida, PalpitePodium
from bolao.services import calcular_pontos_podium_geral

try:
    print("\n=======================================================")
    print("INICIANDO ALOCACAO MASTER DO GABARITO DE PODIO")
    print("=======================================================")

    # 2. Analisa o Jogo 104 (FINAL)
    jogo_104 = Partida.objects.get(numero_jogo=104)
    if jogo_104.gols_casa is not None and jogo_104.gols_visitante is not None:
        if jogo_104.gols_casa > jogo_104.gols_visitante:
            campeao = jogo_104.time_casa
            vice = jogo_104.time_visitante
        elif jogo_104.gols_visitante > jogo_104.gols_casa:
            campeao = jogo_104.time_visitante
            vice = jogo_104.time_casa
        else:
            if jogo_104.vencedor_penaltis == jogo_104.time_casa:
                campeao = jogo_104.time_casa
                vice = jogo_104.time_visitante
            else:
                campeao = jogo_104.time_visitante
                vice = jogo_104.time_casa
        print(f"-> Definido no Banco: Campeao = {campeao} | Vice = {vice}")
    else:
        campeao, vice = None, None
        print("-> Alerta: Jogo 104 nao possui placar cadastrado.")

    # 3. Analisa o Jogo 103 (3o LUGAR)
    jogo_103 = Partida.objects.get(numero_jogo=103)
    if jogo_103.gols_casa is not None and jogo_103.gols_visitante is not None:
        if jogo_103.gols_casa > jogo_103.gols_visitante:
            terceiro = jogo_103.time_casa
            quarto = jogo_103.time_visitante
        elif jogo_103.gols_visitante > jogo_103.gols_casa:
            terceiro = jogo_103.time_visitante
            quarto = jogo_103.time_casa
        else:
            if jogo_103.vencedor_penaltis == jogo_103.time_casa:
                terceiro = jogo_103.time_casa
                quarto = jogo_103.time_visitante
            else:
                terceiro = jogo_103.time_visitante
                quarto = jogo_103.time_casa
        print(f"-> Definido no Banco: 3o Lugar = {terceiro} | 4o Lugar = {quarto}")
    else:
        terceiro, quarto = None, None
        print("-> Alerta: Jogo 103 nao possui placar cadastrado.")

    # 4. Atualiza o Gabarito Oficial (usuario=None)
    podio_real, _ = PalpitePodium.objects.get_or_create(usuario=None)
    if campeao: podio_real.campeao = campeao
    if vice: podio_real.vice = vice
    if terceiro: podio_real.terceiro = terceiro
    if quarto: podio_real.quarto = quarto
    podio_real.save()
    print("\n✅ Linha de Gabarito Oficial (usuario=None) consolidada com sucesso!")

    # 5. Executa a rotina nativa de calculo do seu services.py
    print("🔄 Forcando a atualizacao dos pontos de podio para todos os usuarios...")
    calcular_pontos_podium_geral()
    
    print("\n=======================================================")
    print("🚀 SUCESSO ABSOLUTO: O PODIO COMPLETO FOI PROCESSADO!")
    print("=======================================================\n")

except Exception as e:
    print(f"\n❌ ERRO CRITICO DE PROCESSAMENTO: {e}\n")