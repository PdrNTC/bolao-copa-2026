import os
import django

# 1. Inicializa o ambiente do Django nativamente no servidor
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from bolao.models import Partida, PalpitePodium
from bolao.services import calcular_pontos_podium_geral

# =====================================================================
# CONFIGURACAO DO PLACAR REAL DE PRODUCAO (AJUSTE SE NECESSARIO)
# =====================================================================
GOLS_FRANCA = 4
GOLS_INGLATERRA = 6
VENCEDOR_PENALTIS_NOME = None  # Coloque 'França' ou 'Inglaterra' se houver empate
# =====================================================================

try:
    print("\n=======================================================")
    print("INICIANDO ATUALIZACAO CRITICA DO JOGO 103 EM PRODUCAO")
    print("=======================================================")

    # 2. Busca o Jogo 103 e atualiza os gols
    jogo = Partida.objects.get(numero_jogo=103)
    jogo.gols_casa = GOLS_FRANCA
    jogo.gols_visitante = GOLS_INGLATERRA

    if VENCEDOR_PENALTIS_NOME == 'Franca' or VENCEDOR_PENALTIS_NOME == 'França':
        jogo.vencedor_penaltis = jogo.time_casa
    elif VENCEDOR_PENALTIS_NOME == 'Inglaterra':
        jogo.vencedor_penaltis = jogo.time_visitante

    jogo.save()
    print("-> Passo 1: Gols do Jogo 103 salvos com sucesso!")

    # 3. Determina matematicamente o 3o e 4o colocado para o Gabarito
    if jogo.gols_casa > jogo.gols_visitante:
        time_3_lugar = jogo.time_casa
        time_4_lugar = jogo.time_visitante
    elif jogo.gols_visitante > jogo.gols_casa:
        time_3_lugar = jogo.time_visitante
        time_4_lugar = jogo.time_casa
    else:
        if jogo.vencedor_penaltis == jogo.time_casa:
            time_3_lugar = jogo.time_casa
            time_4_lugar = jogo.time_visitante
        else:
            time_3_lugar = jogo.time_visitante
            time_4_lugar = jogo.time_casa

    # 4. Alimenta o Gabarito Oficial do Banco (usuario=None)
    podio_real, created = PalpitePodium.objects.get_or_create(usuario=None)
    podio_real.terceiro = time_3_lugar
    podio_real.quarto = time_4_lugar
    podio_real.save()
    print(f"-> Passo 2: Gabarito Oficial fixado (3o: {time_3_lugar} | 4o: {time_4_lugar})")

    # 5. Dispara a funcao nativa para processar os 350 e 400 pontos de todo mundo
    print("-> Passo 3: Forcando recalculo do ranking de podios...")
    calcular_pontos_podium_geral()

    print("\n=======================================================")
    print(" SUCESSO: JOGO E PÓDIO ATUALIZADOS EM PRODUÇÃO!")
    print("=======================================================\n")

except Exception as e:
    print(f"\n[ERRO CRITICO EM PRODUCAO]: {e}\n")