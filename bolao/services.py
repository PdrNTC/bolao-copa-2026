from .models import Partida, Palpite, Time, PalpitePodium
from django.db.models import Q
from django.contrib.auth.models import User
from django.db.models import Sum

# ==============================================================================
# 1. LÓGICA DE CLASSIFICAÇÃO (GRUPOS)
# ==============================================================================

def calcular_classificacao_usuario(user):
    """
    Calcula a classificação dos 12 grupos baseado nos palpites do usuário.
    Retorna um dicionário: {'1A': TimeBrasil, '2A': TimeSuica, 'T1': TimeX...}
    """
    classificacao = {} 
    terceiros = []
    grupos = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    
    for grupo in grupos:
        times = Time.objects.filter(grupo=grupo)
        dados_grupo = []
        
        # 🟢 TRAVA DE SEGURANÇA 1: Se for a Realidade (user=None), o grupo precisa ter todos os 6 jogos jogados
        if user is None:
            jogos_concluidos = Partida.objects.filter(
                fase='GRUPOS',
                time_casa__grupo=grupo,
                gols_casa__isnull=False
            ).count()
            
            if jogos_concluidos < 6:
                # Se o grupo não acabou na realidade, os classificados oficiais são nulos por enquanto
                classificacao[f'1{grupo}'] = None
                classificacao[f'2{grupo}'] = None
                continue # Pula para o próximo grupo sem gerar dados fantasmas
        
        for time in times:
            pontos = 0
            saldo = 0
            gols_pro = 0
            
            if user:
                # --- BUSCA BASEADA EM PALPITES (VISÃO DO USUÁRIO) ---
                palpites = Palpite.objects.filter(
                    (Q(partida__time_casa=time) | Q(partida__time_visitante=time)),
                    partida__fase='GRUPOS',
                    usuario=user
                )

                for p in palpites:
                    if p.partida.time_casa and p.partida.time_visitante:
                        gc = p.palpite_casa
                        gv = p.palpite_visitante
                        
                        is_casa = (p.partida.time_casa == time)
                        g_favor = gc if is_casa else gv
                        g_contra = gv if is_casa else gc
                        
                        saldo += (g_favor - g_contra)
                        gols_pro += g_favor
                        
                        if g_favor > g_contra: pontos += 3
                        elif g_favor == g_contra: pontos += 1

            else:
                # --- BUSCA BASEADA EM JOGOS REAIS (VISÃO DO ADMIN) ---
                jogos = Partida.objects.filter(
                    (Q(time_casa=time) | Q(time_visitante=time)),
                    fase='GRUPOS',
                    gols_casa__isnull=False
                )

                for jogo in jogos:
                    gc = jogo.gols_casa
                    gv = jogo.gols_visitante
                    
                    is_casa = (jogo.time_casa == time)
                    g_favor = gc if is_casa else gv
                    g_contra = gv if is_casa else gc
                    
                    saldo += (g_favor - g_contra)
                    gols_pro += g_favor
                    
                    if g_favor > g_contra: pontos += 3
                    elif g_favor == g_contra: pontos += 1

            dados_grupo.append({'time': time, 'pts': pontos, 'saldo': saldo, 'gols': gols_pro})
        
        # Ordena: Pontos > Saldo > Gols
        dados_grupo.sort(key=lambda x: (x['pts'], x['saldo'], x['gols']), reverse=True)
        
        if len(dados_grupo) >= 1: classificacao[f'1{grupo}'] = dados_grupo[0]['time']
        if len(dados_grupo) >= 2: classificacao[f'2{grupo}'] = dados_grupo[1]['time']
        if len(dados_grupo) >= 3:
            t = dados_grupo[2]
            terceiros.append(t)

    # 🟢 TRAVA DE SEGURANÇA 2: Só calcula os melhores 3º colocados se os 12 grupos reais estiverem fechados
    if len(terceiros) == 12:
        terceiros.sort(key=lambda x: (x['pts'], x['saldo'], x['gols']), reverse=True)
        oito_melhores = terceiros[:8]
        
        vagas_oponentes = {}
        jogos_t = Partida.objects.filter(referencia_visitante__startswith='T')
        
        for j in jogos_t:
            if j.referencia_casa and len(j.referencia_casa) == 2:
                vagas_oponentes[j.referencia_visitante] = j.referencia_casa[1]

        alocacao = {}
        disponiveis = list(oito_melhores)

        for i in range(1, 9):
            vaga = f'T{i}'
            grupo_oponente = vagas_oponentes.get(vaga)
            
            time_escolhido = None
            for t in disponiveis:
                if t['time'].grupo != grupo_oponente:
                    time_escolhido = t
                    break
            
            if time_escolhido:
                alocacao[vaga] = time_escolhido['time']
                disponiveis.remove(time_escolhido)
            else:
                if disponiveis:
                    time_problematico = disponiveis[0]
                    alocado_com_sucesso = False
                    
                    for vaga_anterior, time_anterior in alocacao.items():
                        grupo_anterior_oponente = vagas_oponentes.get(vaga_anterior)
                        
                        if time_problematico['time'].grupo != grupo_anterior_oponente and time_anterior.grupo != grupo_oponente:
                            alocacao[vaga] = time_anterior
                            alocacao[vaga_anterior] = time_problematico['time']
                            disponiveis.remove(time_problematico)
                            alocado_com_sucesso = True
                            break
                    
                    if not alocado_com_sucesso:
                        alocacao[vaga] = time_problematico['time']
                        disponiveis.remove(time_problematico)

        for vaga, time in alocacao.items():
            classificacao[vaga] = time
    else:
        # Se a fase de grupos real não acabou, as vagas coringa de 3º ficam vazias
        for i in range(1, 9):
            classificacao[f'T{i}'] = None

    return classificacao


# ==============================================================================
# 2. LÓGICA DE MATA-MATA (REAL - ADMIN)
# ==============================================================================

def atualizar_confrontos():
    """
    Atualiza os times reais nas partidas de mata-mata (Admin).
    """
    classificacao = calcular_classificacao_usuario(user=None)
    jogos_futuros = Partida.objects.exclude(fase='GRUPOS')
    
    for jogo in jogos_futuros:
        mudou = False
        
        novo_casa = resolver_time_real(jogo.referencia_casa, classificacao)
        if novo_casa and jogo.time_casa != novo_casa:
            jogo.time_casa = novo_casa
            mudou = True

        novo_vis = resolver_time_real(jogo.referencia_visitante, classificacao)
        if novo_vis and jogo.time_visitante != novo_vis:
            jogo.time_visitante = novo_vis
            mudou = True
        
        if mudou:
            jogo.save(skip_calc=True)


def resolver_time_real(referencia, classificacao):
    if not referencia: return None
    
    if referencia.startswith('W') or referencia.startswith('L'):
        try:
            num = int(referencia[1:])
            jogo_ant = Partida.objects.get(numero_jogo=num)
            
            if jogo_ant.gols_casa is not None and jogo_ant.gols_visitante is not None:
                vencedor = None
                perdedor = None

                if jogo_ant.gols_casa > jogo_ant.gols_visitante:
                    vencedor = jogo_ant.time_casa
                    perdedor = jogo_ant.time_visitante
                elif jogo_ant.gols_visitante > jogo_ant.gols_casa:
                    vencedor = jogo_ant.time_visitante
                    perdedor = jogo_ant.time_casa
                else:
                    if jogo_ant.vencedor_penaltis == jogo_ant.time_casa:
                        vencedor = jogo_ant.time_casa
                        perdedor = jogo_ant.time_visitante
                    else:
                        vencedor = jogo_ant.time_visitante
                        perdedor = jogo_ant.time_casa
                
                if referencia.startswith('W'): return vencedor
                if referencia.startswith('L'): return perdedor
                
        except: pass
        return None
    
    return classificacao.get(referencia)


# ==============================================================================
# 3. LÓGICA DE PONTUAÇÃO DOS GRUPOS
# ==============================================================================

def calcular_pontos_classificacao_grupos():
    """ REGRA: 75 (Ordem exata), 40 (Invertido), 55 (Só o 1º), 50 (Só o 2º) """
    classificacao_real = calcular_classificacao_usuario(user=None)
    if not classificacao_real: return
        
    letras_grupos = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    
    for user in User.objects.all():
        pontos_ganhos = 0
        classificacao_user = calcular_classificacao_usuario(user)
        
        for letra in letras_grupos:
            c1_real = classificacao_real.get(f'1{letra}')
            c2_real = classificacao_real.get(f'2{letra}')
            c1_user = classificacao_user.get(f'1{letra}')
            c2_user = classificacao_user.get(f'2{letra}')
            
            # 🟢 SÓ COMPARA SE O GRUPO REAL JÁ ESTIVER TOTALMENTE DEFINIDO
            if c1_real is not None and c2_real is not None:
                if c1_user == c1_real and c2_user == c2_real:
                    pontos_ganhos += 75
                elif c1_user == c2_real and c2_user == c1_real:
                    pontos_ganhos += 40
                elif c1_user == c1_real:
                    pontos_ganhos += 55
                elif c2_user == c2_real:
                    pontos_ganhos += 50
                
        podio, _ = PalpitePodium.objects.get_or_create(usuario=user)
        podio.pontos_fase_grupos = pontos_ganhos
        podio.save()


# ==============================================================================
# 4. LÓGICA DE PONTUAÇÃO DO MATA-MATA
# ==============================================================================

def calcular_pontos_confrontos_matamata():
    """ REGRA: Parcial vs Completo nas Fases Finais """
    from .utils import resolver_partida_mata_mata
    
    tabela_pontos = {
        '16AVOS': {'parcial': 0, 'completo': 0},
        'OITAVAS': {'parcial': 100, 'completo': 150},
        'QUARTAS': {'parcial': 175, 'completo': 200},
        'SEMI': {'parcial': 225, 'completo': 250},
        '3LUGAR': {'parcial': 275, 'completo': 300},
        'FINAL': {'parcial': 325, 'completo': 350},
    }
    
    # Só pontua partidas de mata-mata cujos times reais já estejam definidos em campo
    jogos_reais = Partida.objects.exclude(fase='GRUPOS').filter(time_casa__isnull=False, time_visitante__isnull=False)
    
    for user in User.objects.all():
        pontos_confronto = 0
        classificados_user = calcular_classificacao_usuario(user)
        
        for jogo in jogos_reais:
            tc_user, tv_user = resolver_partida_mata_mata(jogo, classificados_user, user)
            
            if tc_user and tv_user:
                times_reais = {jogo.time_casa.id, jogo.time_visitante.id}
                times_user = {tc_user.id, tv_user.id}
                
                acertos = len(times_reais.intersection(times_user))
                fase = jogo.fase
                
                if acertos == 2:
                    pontos_confronto += tabela_pontos[fase]['completo']
                elif acertos == 1:
                    pontos_confronto += tabela_pontos[fase]['parcial']
                    
        podio, _ = PalpitePodium.objects.get_or_create(usuario=user)
        podio.pontos_confrontos = pontos_confronto
        podio.save()


# ==============================================================================
# 5. LÓGICA DE PÓDIO FINAL (CAMPEÃO, VICE...)
# ==============================================================================

def calcular_pontos_podium_geral():
    """ REGRA: 500 (Campeão), 450 (Vice), 400 (3º), 350 (4º) """
    from .utils import simular_caminho_usuario
    
    for u in User.objects.all():
        simular_caminho_usuario(u)
        
    podio_real = PalpitePodium.objects.filter(usuario=None).first()
    if not podio_real:
        simular_caminho_usuario(None)
        podio_real = PalpitePodium.objects.filter(usuario=None).first()

    if not podio_real: return

    for podio_user in PalpitePodium.objects.exclude(usuario=None):
        pts_campeao = 500 if (podio_user.campeao and podio_real.campeao and podio_user.campeao == podio_real.campeao) else 0
        pts_vice = 450 if (podio_user.vice and podio_real.vice and podio_user.vice == podio_real.vice) else 0
        pts_terceiro = 400 if (podio_user.terceiro and podio_real.terceiro and podio_user.terceiro == podio_real.terceiro) else 0
        pts_quarto = 350 if (podio_user.quarto and podio_real.quarto and podio_user.quarto == podio_real.quarto) else 0
        
        podio_user.pontos_campeao = pts_campeao
        podio_user.pontio_vice = pts_vice  # Mantido histórico
        podio_user.pontos_vice = pts_vice
        podio_user.pontos_terceiro = pts_terceiro
        podio_user.pontos_quarto = pts_quarto
        podio_user.save()


def verificar_fase_grupos_completa(user):
    if not user.is_authenticated:
        return False
        
    total_jogos_grupo = Partida.objects.filter(fase='GRUPOS').count()
    total_palpites_user = Palpite.objects.filter(usuario=user, partida__fase='GRUPOS').count()
    
    return total_palpites_user == total_jogos_grupo