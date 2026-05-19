from .models import Partida, Palpite, Time, PalpitePodium
from django.db.models import Q
from bolao.models import Time, Partida

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
        
        for time in times:
            pontos = 0
            saldo = 0
            gols_pro = 0
            
            if user:
                # --- BUSCA BASEADA EM PALPITES (VISÃO DO USUÁRIO) ---
                # Correção: Usamos partida__time_casa porque estamos na tabela Palpite
                palpites = Palpite.objects.filter(
                    (Q(partida__time_casa=time) | Q(partida__time_visitante=time)),
                    partida__fase='GRUPOS',
                    usuario=user
                )

                for p in palpites:
                    # Verifica se o palpite está completo
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
                # Correção: Usamos time_casa direto porque estamos na tabela Partida
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

    # Melhores 3º colocados
    terceiros.sort(key=lambda x: (x['pts'], x['saldo'], x['gols']), reverse=True)
    for i, t in enumerate(terceiros[:8]):
        classificacao[f'T{i+1}'] = t['time']

    return classificacao


# ==============================================================================
# 2. LÓGICA DE MATA-MATA (REAL - ADMIN)
# ==============================================================================

def atualizar_confrontos():
    """
    Atualiza os times reais nas partidas de mata-mata (Admin).
    """
    # Passo 1: Calcula classificação real (user=None)
    classificacao = calcular_classificacao_usuario(user=None)
    
    # Passo 2: Atualiza jogos
    jogos_futuros = Partida.objects.exclude(fase='GRUPOS')
    
    for jogo in jogos_futuros:
        mudou = False
        
        # Resolve Time Casa
        novo_casa = resolver_time_real(jogo.referencia_casa, classificacao)
        if novo_casa and jogo.time_casa != novo_casa:
            jogo.time_casa = novo_casa
            mudou = True

        # Resolve Time Visitante
        novo_vis = resolver_time_real(jogo.referencia_visitante, classificacao)
        if novo_vis and jogo.time_visitante != novo_vis:
            jogo.time_visitante = novo_vis
            mudou = True
        
        if mudou:
            jogo.save()


def resolver_time_real(referencia, classificacao):
    if not referencia: return None
    
    # Lógica de Vencedor (W) e Perdedor (L)
    if referencia.startswith('W') or referencia.startswith('L'):
        try:
            num = int(referencia[1:])
            jogo_ant = Partida.objects.get(numero_jogo=num)
            
            # Só calcula se o jogo da vida real já aconteceu (tem os dois placares preenchidos)
            if jogo_ant.gols_casa is not None and jogo_ant.gols_visitante is not None:
                vencedor = None
                perdedor = None

                # Vitória no tempo normal
                if jogo_ant.gols_casa > jogo_ant.gols_visitante:
                    vencedor = jogo_ant.time_casa
                    perdedor = jogo_ant.time_visitante
                elif jogo_ant.gols_visitante > jogo_ant.gols_casa:
                    vencedor = jogo_ant.time_visitante
                    perdedor = jogo_ant.time_casa
                # Empate na vida real: Lê o novo campo do Admin
                else:
                    if jogo_ant.vencedor_penaltis == jogo_ant.time_casa:
                        vencedor = jogo_ant.time_casa
                        perdedor = jogo_ant.time_visitante
                    else:
                        vencedor = jogo_ant.time_visitante
                        perdedor = jogo_ant.time_casa
                
                # Retorna o correto
                if referencia.startswith('W'): return vencedor
                if referencia.startswith('L'): return perdedor
                
        except: pass
        return None
    
    return classificacao.get(referencia)


# ==============================================================================
# 3. LÓGICA DE PÓDIO (PONTUAÇÃO FINAL)
# ==============================================================================

def calcular_pontos_podium_geral():
    # (Mantém a lógica que você já tinha aqui, está correta)
    # ... código do calcular_pontos_podium_geral ...
    pass # Cole o código que você já tinha aqui se quiser, ou use o do utils abaixo


# ==============================================================================
# 4. LÓGICA DE PONTUAÇÃO
# ==============================================================================

def calcular_classificacao_grupo_real(letra_grupo):
    """
    Calcula a tabela de classificação real de um grupo 
    baseada nos resultados (gols) oficiais cadastrados no Admin.
    """
    times = Time.objects.filter(grupo=letra_grupo)
    tabela = []
    
    for time in times:
        pontos = 0
        saldo_gols = 0
        gols_pro = 0
        
        # Partidas como Mandante (Casa) que já têm resultado
        jogos_casa = Partida.objects.filter(time_casa=time, fase='GRUPOS', gols_casa__isnull=False)
        for j in jogos_casa:
            saldo_gols += (j.gols_casa - j.gols_visitante)
            gols_pro += j.gols_casa
            if j.gols_casa > j.gols_visitante: pontos += 3
            elif j.gols_casa == j.gols_visitante: pontos += 1
            
        # Partidas como Visitante que já têm resultado
        jogos_vis = Partida.objects.filter(time_visitante=time, fase='GRUPOS', gols_visitante__isnull=False)
        for j in jogos_vis:
            saldo_gols += (j.gols_visitante - j.gols_casa)
            gols_pro += j.gols_visitante
            if j.gols_visitante > j.gols_casa: pontos += 3
            elif j.gols_visitante == j.gols_casa: pontos += 1
            
        tabela.append({
            'time': time,
            'pontos': pontos,
            'saldo_gols': saldo_gols,
            'gols_pro': gols_pro
        })
    
    # Ordena a tabela por Pontos > Saldo de Gols > Gols Pró
    tabela.sort(key=lambda x: (x['pontos'], x['saldo_gols'], x['gols_pro']), reverse=True)
    return tabela