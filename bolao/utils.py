from .models import Partida, Palpite, PalpitePodium
from .services import calcular_classificacao_usuario # Agora importamos de lá!

# ==============================================================================
# LÓGICA DE SIMULAÇÃO (CAMINHO DO USUÁRIO)
# ==============================================================================

def resolver_partida_mata_mata(partida, classificados_usuario, user):
    """
    Retorna (time_casa, time_visitante) virtuais para exibir na tela do usuário.
    """
    tc = resolver_time_virtual(partida.referencia_casa, classificados_usuario, user)
    tv = resolver_time_virtual(partida.referencia_visitante, classificados_usuario, user)
    return tc, tv

def resolver_time_virtual(referencia, classificados, user):
    if not referencia: return None
    
    # Referência de Grupo (1A, 2B...)
    if referencia in classificados:
        return classificados[referencia]
    
    # Referência de Jogo Anterior (W=Winner, L=Loser)
    if referencia.startswith('W') or referencia.startswith('L'):
        try:
            num = int(referencia[1:]) # Pega o número (ex: 101)
            jogo_ant = Partida.objects.get(numero_jogo=num)
            
            # Recursão: Quem joga esse jogo anterior?
            tc_ant, tv_ant = resolver_partida_mata_mata(jogo_ant, classificados, user)
            
            # Qual foi o palpite do usuário?
            palpite = Palpite.objects.filter(usuario=user, partida=jogo_ant).first()
            
            if palpite and tc_ant and tv_ant:
                p_casa = palpite.palpite_casa
                p_vis = palpite.palpite_visitante
                
                # LÓGICA DO VENCEDOR (W)
                if referencia.startswith('W'):
                    if p_casa > p_vis: return tc_ant
                    elif p_vis > p_casa: return tv_ant
                    return tc_ant # Empate no palpite (Default Casa)

                # LÓGICA DO PERDEDOR (L) - NOVA!
                elif referencia.startswith('L'):
                    if p_casa > p_vis: return tv_ant # Se Casa ganhou, Perdedor é Visitante
                    elif p_vis > p_casa: return tc_ant # Se Vis ganhou, Perdedor é Casa
                    return tv_ant # Empate no palpite (Default Visitante)

        except: pass
    
    return None

def simular_caminho_usuario(user):
    """
    Salva o pódio virtual do usuário.
    """
    # 1. Calcula a base (fase de grupos)
    classificados = calcular_classificacao_usuario(user)
    
    # 2. Simula Final
    jogo_final = Partida.objects.filter(fase='FINAL').first()
    jogo_terceiro = Partida.objects.filter(fase='3LUGAR').first()
    
    if not jogo_final: return

    # Descobre campeão/vice
    tc_final, tv_final = resolver_partida_mata_mata(jogo_final, classificados, user)
    palpite_final = Palpite.objects.filter(usuario=user, partida=jogo_final).first()
    
    campeao = None
    vice = None
    
    if palpite_final and tc_final and tv_final:
        if palpite_final.palpite_casa > palpite_final.palpite_visitante:
            campeao = tc_final
            vice = tv_final
        else:
            campeao = tv_final
            vice = tc_final
            
    # Descobre 3º/4º
    terceiro = None
    quarto = None
    if jogo_terceiro:
        tc_3, tv_3 = resolver_partida_mata_mata(jogo_terceiro, classificados, user)
        palpite_3 = Palpite.objects.filter(usuario=user, partida=jogo_terceiro).first()
        if palpite_3 and tc_3 and tv_3:
             if palpite_3.palpite_casa > palpite_3.palpite_visitante:
                terceiro = tc_3
                quarto = tv_3
             else:
                terceiro = tv_3
                quarto = tc_3

    # Salva
    podium, _ = PalpitePodium.objects.get_or_create(usuario=user)
    podium.campeao = campeao
    podium.vice = vice
    podium.terceiro = terceiro
    podium.quarto = quarto
    podium.save()