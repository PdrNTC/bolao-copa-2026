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
    # Ordena: Pontos > Saldo > Gols
    terceiros.sort(key=lambda x: (x['pts'], x['saldo'], x['gols']), reverse=True)
    oito_melhores = terceiros[:8]

    # =========================================================================
    # INÍCIO DO ALGORITMO ANTI-COLISÃO (EMBARALHADOR INTELIGENTE)
    # =========================================================================
    
    # 1. Descobre de qual grupo é o adversário de cada vaga T (T1 a T8)
    # Ex: Se o T1 joga contra o "1A", o oponente do T1 é do grupo "A".
    vagas_oponentes = {}
    jogos_t = Partida.objects.filter(referencia_visitante__startswith='T')
    
    for j in jogos_t:
        if j.referencia_casa and len(j.referencia_casa) == 2:
            vagas_oponentes[j.referencia_visitante] = j.referencia_casa[1] # Pega só a letra do grupo

    # 2. Distribui os crachás evitando que o time pegue o próprio grupo
    alocacao = {}
    disponiveis = list(oito_melhores)

    for i in range(1, 9):
        vaga = f'T{i}'
        grupo_oponente = vagas_oponentes.get(vaga)
        
        # Tenta achar o melhor time disponível que NÃO seja do grupo do oponente
        time_escolhido = None
        for t in disponiveis:
            if t['time'].grupo != grupo_oponente:
                time_escolhido = t
                break
        
        if time_escolhido:
            alocacao[vaga] = time_escolhido['time']
            disponiveis.remove(time_escolhido)
        else:
            # LÓGICA DE SWAP (TROCA INTELIGENTE)
            # Se todos os que sobraram dão colisão, ele pede para "trocar figurinha" 
            # com uma vaga anterior que já estava resolvida.
            if disponiveis:
                time_problematico = disponiveis[0]
                alocado_com_sucesso = False
                
                for vaga_anterior, time_anterior in alocacao.items():
                    grupo_anterior_oponente = vagas_oponentes.get(vaga_anterior)
                    
                    # Testa se a troca resolve o problema para os dois lados
                    if time_problematico['time'].grupo != grupo_anterior_oponente and time_anterior.grupo != grupo_oponente:
                        alocacao[vaga] = time_anterior
                        alocacao[vaga_anterior] = time_problematico['time']
                        disponiveis.remove(time_problematico)
                        alocado_com_sucesso = True
                        break
                
                if not alocado_com_sucesso:
                    # Fallback absoluto de segurança (evita travar o sistema)
                    alocacao[vaga] = time_problematico['time']
                    disponiveis.remove(time_problematico)

    # 3. Grava a alocação final e oficial no dicionário de classificação
    for vaga, time in alocacao.items():
        classificacao[vaga] = time

    # =========================================================================
    # FIM DO ALGORITMO ANTI-COLISÃO
    # =========================================================================

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
            # A MÁGICA ESTÁ AQUI: Evita o loop infinito!
            jogo.save(skip_calc=True)


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


### FUNÇÃO PARA CALCULAR OS PONTOS DOS VENCEDORES DOS GRUPOS ###
# 1° Lugar e 2° Lugar
def calcular_pontos_classificacao_grupos():
    """ REGRA: 75 (Ordem exata), 40 (Invertido), 55 (Só o 1º), 50 (Só o 2º) """
    from .models import User, PalpitePodium
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
            
            # Só calcula se a vida real já definiu os dois classificados do grupo
            if c1_real and c2_real:
                if c1_user == c1_real and c2_user == c2_real:
                    pontos_ganhos += 75  # Acertou os dois na ordem
                elif c1_user == c2_real and c2_user == c1_real:
                    pontos_ganhos += 40  # Acertou os classificados, mas invertidos
                elif c1_user == c1_real:
                    pontos_ganhos += 55  # Acertou só o 1º colocado
                elif c2_user == c2_real:
                    pontos_ganhos += 50  # Acertou só o 2º colocado
                
        podio, _ = PalpitePodium.objects.get_or_create(usuario=user)
        podio.pontos_fase_grupos = pontos_ganhos
        podio.save()



def calcular_pontos_confrontos_matamata():
    """ REGRA: Parcial vs Completo nas Fases Finais """
    from .models import User, PalpitePodium, Partida
    from .utils import resolver_partida_mata_mata
    
    # ⚠️ NOTA: Você não especificou pontos para os '16AVOS' na regra, então coloquei 0. 
    # Se quiser dar pontos para 16-avos, é só trocar os zeros aqui embaixo!
    tabela_pontos = {
        '16AVOS': {'parcial': 0, 'completo': 0},
        'OITAVAS': {'parcial': 100, 'completo': 150},
        'QUARTAS': {'parcial': 175, 'completo': 200},
        'SEMI': {'parcial': 225, 'completo': 250},
        '3LUGAR': {'parcial': 275, 'completo': 300},
        'FINAL': {'parcial': 325, 'completo': 350},
    }
    
    # Pega apenas jogos do mata-mata que JÁ ESTÃO DEFINIDOS na vida real
    jogos_reais = Partida.objects.exclude(fase='GRUPOS').filter(time_casa__isnull=False, time_visitante__isnull=False)
    
    for user in User.objects.all():
        pontos_confronto = 0
        classificados_user = calcular_classificacao_usuario(user)
        
        for jogo in jogos_reais:
            # Pega quem o usuário achava que ia jogar esta partida
            tc_user, tv_user = resolver_partida_mata_mata(jogo, classificados_user, user)
            
            if tc_user and tv_user:
                # Usamos conjuntos (sets) para ignorar a ordem de Casa x Visitante
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

 

def calcular_pontos_podium_geral():
    """ REGRA: 500 (Campeão), 450 (Vice), 400 (3º), 350 (4º) """
    from .models import User, PalpitePodium
    from .utils import simular_caminho_usuario
    
    # 1. Garante que os palpites dos usuários geraram os pódios virtuais deles
    for u in User.objects.all():
        simular_caminho_usuario(u)
        
    # 2. Pega o Pódio Real da vida real (user=None)
    podio_real = PalpitePodium.objects.filter(usuario=None).first()
    if not podio_real:
        # Se não existe usuário None (Pódio Oficial), cria temporariamente para cálculo
        simular_caminho_usuario(None)
        podio_real = PalpitePodium.objects.filter(usuario=None).first()

    if not podio_real: return

    for podio_user in PalpitePodium.objects.exclude(usuario=None):
        pts_campeao = 500 if (podio_user.campeao and podio_real.campeao and podio_user.campeao == podio_real.campeao) else 0
        pts_vice = 450 if (podio_user.vice and podio_real.vice and podio_user.vice == podio_real.vice) else 0
        pts_terceiro = 400 if (podio_user.terceiro and podio_real.terceiro and podio_user.terceiro == podio_real.terceiro) else 0
        pts_quarto = 350 if (podio_user.quarto and podio_real.quarto and podio_user.quarto == podio_real.quarto) else 0
        
        podio_user.pontos_campeao = pts_campeao
        podio_user.pontos_vice = pts_vice
        podio_user.pontos_terceiro = pts_terceiro
        podio_user.pontos_quarto = pts_quarto
        podio_user.save()