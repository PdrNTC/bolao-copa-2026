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
    
    if referencia in classificados:
        return classificados[referencia]
    
    if referencia.startswith('W') or referencia.startswith('L'):
        try:
            num = int(referencia[1:])
            jogo_ant = Partida.objects.get(numero_jogo=num)
            tc_ant, tv_ant = resolver_partida_mata_mata(jogo_ant, classificados, user)
            palpite = Palpite.objects.filter(usuario=user, partida=jogo_ant).first()
            
            if palpite and tc_ant and tv_ant:
                p_casa = int(palpite.palpite_casa)
                p_vis = int(palpite.palpite_visitante)
                
                # --- AJUSTE: LÓGICA DO VENCEDOR (W) ---
                if referencia.startswith('W'):
                    if p_casa > p_vis: 
                        return tc_ant
                    elif p_vis > p_casa: 
                        return tv_ant
                    else:
                        # Se escolheu o visitante nos pênaltis, ele passa. 
                        # Caso contrário (ou se None), passa o da casa.
                        id_salvo = str(palpite.vencedor_confronto_id)
                        id_visitante = str(tv_ant.id)
                        if id_salvo == id_visitante:
                            return tv_ant
                        return tc_ant

                # --- AJUSTE: LÓGICA DO PERDEDOR (L) ---
                elif referencia.startswith('L'):
                    if p_casa > p_vis: 
                        return tv_ant 
                    elif p_vis > p_casa: 
                        return tc_ant 
                    else:
                        # Se o visitante foi o vencedor escolhido, o perdedor É A CASA.
                        # Isso impede que o mesmo time vá para a Final e para o 3º lugar.
                        id_salvo = str(palpite.vencedor_confronto_id)
                        id_visitante = str(tv_ant.id)
                        if id_salvo == id_visitante:
                            return tc_ant
                        return tv_ant

        except: pass
    return None

def simular_caminho_usuario(user):
    """
    Atualiza o Pódio Virtual (Campeão, Vice, 3º e 4º)
    """
    classificados = calcular_classificacao_usuario(user)
    
    jogo_final = Partida.objects.filter(fase='FINAL').first()
    jogo_terceiro = Partida.objects.filter(fase='3LUGAR').first()
    
    if not jogo_final: return

    # --- LÓGICA DA FINAL ---
    tc_f, tv_f = resolver_partida_mata_mata(jogo_final, classificados, user)
    palp_f = Palpite.objects.filter(usuario=user, partida=jogo_final).first()
    
    campeao, vice = None, None
    if palp_f and tc_f and tv_f:
        if palp_f.palpite_casa > palp_f.palpite_visitante:
            campeao, vice = tc_f, tv_f
        elif palp_f.palpite_visitante > palp_f.palpite_casa:
            campeao, vice = tv_f, tc_f
        else:
            # AJUSTE: Respeita os pênaltis na Final
            id_s = str(palp_f.vencedor_confronto_id)
            if id_s == str(tv_f.id):
                campeao, vice = tv_f, tc_f
            else:
                campeao, vice = tc_f, tv_f
            
    # --- LÓGICA DO 3º LUGAR ---
    terceiro, quarto = None, None
    if jogo_terceiro:
        tc_3, tv_3 = resolver_partida_mata_mata(jogo_terceiro, classificados, user)
        palp_3 = Palpite.objects.filter(usuario=user, partida=jogo_terceiro).first()
        if palp_3 and tc_3 and tv_3:
             if palp_3.palpite_casa > palp_3.palpite_visitante:
                terceiro, quarto = tc_3, tv_3
             elif palp_3.palpite_visitante > palp_3.palpite_casa:
                terceiro, quarto = tv_3, tc_3
             else:
                # AJUSTE: Respeita os pênaltis no 3º lugar
                id_s = str(palp_3.vencedor_confronto_id)
                if id_s == str(tv_3.id):
                    terceiro, quarto = tv_3, tc_3
                else:
                    terceiro, quarto = tc_3, tv_3

    # Salva no banco de dados
    podium, _ = PalpitePodium.objects.get_or_create(usuario=user)
    podium.campeao, podium.vice = campeao, vice
    podium.terceiro, podium.quarto = terceiro, quarto
    podium.save()