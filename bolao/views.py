from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

# Importe os novos Models e Utils
from .models import Partida, Palpite, PalpiteExtra, PerguntaExtra, PalpitePodium, Time
# Importa a classificação do services, e o resto do utils
from .services import calcular_classificacao_usuario 
from .utils import resolver_partida_mata_mata, simular_caminho_usuario

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib import messages  # Importante para exibir os erros na tela

# --- RANKING ATUALIZADO --- #
@login_required # Adicionando Login obrigatorio #
def ranking(request):
    usuarios = User.objects.all()
    dados_ranking = []

    for usuario in usuarios:
        # 1. Soma pontos de TODAS as partidas (Grupos + Mata-Mata)
        # Note que agora usamos o campo 'pontos' (não mais pontos_ganhos) conforme seu novo model
        soma_partidas = Palpite.objects.filter(usuario=usuario).aggregate(
            total=Sum('pontos'))['total'] or 0
        
        # 2. Soma pontos do Pódio Automático (Campeão, Vice...)
        podium = PalpitePodium.objects.filter(usuario=usuario).first()
        soma_podium = podium.total_pontos() if podium else 0

        # 3. Soma pontos Extras Manuais (Se você manteve as perguntas extras)
        soma_extras = PalpiteExtra.objects.filter(usuario=usuario).aggregate(
            total=Sum('pontos_ganhos'))['total'] or 0
        
        # Total Geral
        total_geral = soma_partidas + soma_podium + soma_extras

        dados_ranking.append({
            'username': usuario.username,
            'total_pontos': total_geral,
            'detalhes': { # Opcional: para debug
                'jogos': soma_partidas,
                'podium': soma_podium,
                'extras': soma_extras
            }
        })
    
    # Ordena do maior para o menor
    dados_ranking.sort(key=lambda x: x['total_pontos'], reverse=True)

    return render(request, 'ranking.html', {'usuarios': dados_ranking})


# --- PALPITES MATA-MATA INTELIGENTE ---
@login_required
def palpites_matamata(request):

    # TRAVA ADICIONADA: Impede acesso se não terminou os 72 jogos de grupos
    total_grupos = Partida.objects.filter(fase='GRUPOS').count()
    meus_palpites_grupos = Palpite.objects.filter(usuario=request.user, partida__fase='GRUPOS').count()
    
    if meus_palpites_grupos < total_grupos:
        messages.warning(request, "Você precisa preencher todos os palpites da Fase de Grupos antes de acessar o Mata-Mata!")
        return redirect('palpites') # Ajuste para o 'name' da sua URL de grupos se for diferente


    fases_finais = ['16AVOS', 'OITAVAS', 'QUARTAS', 'SEMI', '3LUGAR', 'FINAL']
    
    if request.method == 'POST':
        partidas = Partida.objects.filter(fase__in=fases_finais)
        for partida in partidas:
            placar_casa = request.POST.get(f'gols_casa_{partida.id}')
            placar_vis = request.POST.get(f'gols_vis_{partida.id}')

            if placar_casa is not None and placar_casa != '' and placar_vis is not None and placar_vis != '':
                vencedor_id = request.POST.get(f'vencedor_{partida.id}')
                
                # --- INÍCIO DO RASTREADOR 1 ---
                #print(f"\n[DEBUG VIEWS] Jogo ID: {partida.id} | Casa: {placar_casa} x Vis: {placar_vis}")
                #print(f"[DEBUG VIEWS] O HTML enviou o Vencedor ID: '{vencedor_id}'")
                # --- FIM DO RASTREADOR 1 ---

                dados_palpite = {
                    'palpite_casa': int(placar_casa),
                    'palpite_visitante': int(placar_vis),
                }
                
                if vencedor_id:
                    dados_palpite['vencedor_confronto_id'] = int(vencedor_id)
                else:
                    dados_palpite['vencedor_confronto_id'] = None 

                palpite_salvo, created = Palpite.objects.update_or_create(
                    usuario=request.user,
                    partida=partida,
                    defaults=dados_palpite
                )
                
                # --- INÍCIO DO RASTREADOR 2 ---
                #print(f"[DEBUG VIEWS] O Banco de Dados salvou o Vencedor ID: '{palpite_salvo.vencedor_confronto_id}'\n")
                # --- FIM DO RASTREADOR 2 ---
        
        simular_caminho_usuario(request.user)
        return redirect('ranking')

    else:
        classificados = calcular_classificacao_usuario(request.user)
        partidas = Partida.objects.filter(fase__in=fases_finais).order_by('numero_jogo')
        lista_jogos = []

        for partida in partidas:
            t_casa, t_vis = resolver_partida_mata_mata(partida, classificados, request.user)
            palpite = Palpite.objects.filter(usuario=request.user, partida=partida).first()

            # EXTRAÍMOS OS IDS DIRETAMENTE AQUI PARA O HTML NÃO SE PERDER
            id_casa_real = t_casa.id if (t_casa and hasattr(t_casa, 'id')) else None
            id_vis_real = t_vis.id if (t_vis and hasattr(t_vis, 'id')) else None

            lista_jogos.append({
                'partida': partida,
                'time_casa_visual': t_casa if t_casa else {'nome': f'({partida.referencia_casa})', 'imagem': ''},
                'time_vis_visual': t_vis if t_vis else {'nome': f'({partida.referencia_visitante})', 'imagem': ''},
                
                # ESTAS DUAS LINHAS SÃO A CHAVE DA SOLUÇÃO:
                'id_casa_puro': id_casa_real,
                'id_vis_puro': id_vis_real,

                'palpite_casa': palpite.palpite_casa if palpite else '',
                'palpite_vis': palpite.palpite_visitante if palpite else '',
                'vencedor_confronto_id': palpite.vencedor_confronto_id if palpite else None
            })

        return render(request, 'palpites_matamata.html', {'lista_jogos': lista_jogos})


# --- OUTRAS VIEWS (Mantidas iguais ou levemente ajustadas) ---

@login_required
def meus_palpites(request):
    # Verifica se já palpitou GRUPOS
    ja_palpitou = Palpite.objects.filter(usuario=request.user, partida__fase='GRUPOS').exists()

    if request.method == 'POST':
        if ja_palpitou: return redirect('etapa_16avos') # Se já foi, avança

        partidas = Partida.objects.filter(fase='GRUPOS')
        for partida in partidas:
            gc = request.POST.get(f'gols_casa_{partida.id}')
            gv = request.POST.get(f'gols_vis_{partida.id}')
            if gc and gv:
                Palpite.objects.update_or_create(
                    usuario=request.user, partida=partida,
                    defaults={'palpite_casa': int(gc), 'palpite_visitante': int(gv)}
                )
        
        # Salva e joga para a próxima etapa
        return redirect('etapa_16avos')

    else:
        partidas = Partida.objects.filter(fase='GRUPOS').order_by('data_jogo')
        lista_jogos = []
        for p in partidas:
            palpite = Palpite.objects.filter(usuario=request.user, partida=p).first()
            lista_jogos.append({
                'partida': p,
                'palpite_casa': palpite.palpite_casa if palpite else '',
                'palpite_vis': palpite.palpite_visitante if palpite else ''
            })
        
        # Se já palpitou, mostra botão "Ir para Próxima Fase" no HTML
        return render(request, 'palpites.html', {'lista_jogos': lista_jogos, 'ja_palpitou': ja_palpitou})
    

def gerenciar_etapa(request, fases_da_etapa, titulo_etapa, proxima_url, progresso_val):
    """
    Controla qualquer etapa do mata-mata: verifica bloqueio, salva, simula e redireciona.
    """

    # TRAVA ADICIONADA: Se tentar burlar digitando a URL de qualquer fase, o sistema barra aqui
    total_grupos = Partida.objects.filter(fase='GRUPOS').count()
    meus_palpites_grupos = Palpite.objects.filter(usuario=request.user, partida__fase='GRUPOS').count()
    
    if meus_palpites_grupos < total_grupos:
        messages.warning(request, "Você precisa preencher todos os palpites da Fase de Grupos antes de acessar o Mata-Mata!")
        return redirect('palpites')


    # Verifica se essa etapa ESPECÍFICA já foi preenchida
    ja_preencheu_etapa = Palpite.objects.filter(
        usuario=request.user, 
        partida__fase__in=fases_da_etapa
    ).exists()

    if request.method == 'POST':
        if ja_preencheu_etapa:
            return redirect(proxima_url)

        partidas = Partida.objects.filter(fase__in=fases_da_etapa)
        for partida in partidas:
            gc = request.POST.get(f'gols_casa_{partida.id}')
            gv = request.POST.get(f'gols_vis_{partida.id}')
            
            # --- ADICIONADO: Captura do vencedor do confronto ---
            vencedor_id = request.POST.get(f'vencedor_{partida.id}')

            if gc is not None and gc != '' and gv is not None and gv != '':
                dados_palpite = {
                    'palpite_casa': int(gc),
                    'palpite_visitante': int(gv),
                }

                # --- ADICIONADO: Lógica para salvar o vencedor ---
                if vencedor_id:
                    dados_palpite['vencedor_confronto_id'] = int(vencedor_id)
                else:
                    dados_palpite['vencedor_confronto_id'] = None

                Palpite.objects.update_or_create(
                    usuario=request.user, 
                    partida=partida,
                    defaults=dados_palpite
                )
        
        simular_caminho_usuario(request.user)
        return redirect(proxima_url)

    else:
        classificados = calcular_classificacao_usuario(request.user)
        partidas = Partida.objects.filter(fase__in=fases_da_etapa).order_by('numero_jogo')
        lista_jogos = []

        def formatar_nome(ref):
            if not ref: return "A Definir"
            if ref.startswith('W'): return f"Vencedor Jogo {ref[1:]}"
            if ref.startswith('L'): return f"Perdedor Jogo {ref[1:]}"
            if ref.startswith('T'): return f"3º Melhor ({ref})"
            if len(ref) == 2: return f"{ref[0]}º do Grupo {ref[1]}"
            return ref

        for partida in partidas:
            t_casa, t_vis = resolver_partida_mata_mata(partida, classificados, request.user)
            palpite = Palpite.objects.filter(usuario=request.user, partida=partida).first()

            # --- ADICIONADO: Extração dos IDs puros para o HTML ---
            id_casa_real = t_casa.id if (t_casa and hasattr(t_casa, 'id')) else None
            id_vis_real = t_vis.id if (t_vis and hasattr(t_vis, 'id')) else None

            lista_jogos.append({
                'partida': partida,
                'time_casa_visual': t_casa if t_casa else {'nome': formatar_nome(partida.referencia_casa), 'imagem': ''},
                'time_vis_visual': t_vis if t_vis else {'nome': formatar_nome(partida.referencia_visitante), 'imagem': ''},
                
                # SÃO ESSAS VARIÁVEIS QUE O SEU HTML USA:
                'id_casa_puro': id_casa_real,
                'id_vis_puro': id_vis_real,

                'palpite_casa': palpite.palpite_casa if palpite else '',
                'palpite_vis': palpite.palpite_visitante if palpite else '',
                'vencedor_confronto_id': palpite.vencedor_confronto_id if palpite else None
            })

        return render(request, 'etapa_matamata.html', {
            'lista_jogos': lista_jogos,
            'titulo': titulo_etapa,
            'ja_preencheu': ja_preencheu_etapa,
            'proxima_url': proxima_url,
            'progresso': progresso_val
        })

def cadastro(request):
    if request.method == 'POST':
        # 1. Captura os dados exatamente como estão no 'name' dos inputs do HTML
        usuario_txt = request.POST.get('username')
        email_txt = request.POST.get('email')
        senha_txt = request.POST.get('password')
        confirma_senha_txt = request.POST.get('confirm_password')
        
        # 2. Validação: As senhas precisam ser iguais
        if senha_txt != confirma_senha_txt:
            messages.error(request, "As senhas não coincidem!")
            return render(request, 'registration/cadastro.html')
            
        # 3. Validação: O nome de usuário deve ser único
        if User.objects.filter(username=usuario_txt).exists():
            messages.error(request, "Este nome de usuário já está em uso!")
            return render(request, 'registration/cadastro.html')
            
        # 4. Validação: O e-mail deve ser único (evita duas contas com o mesmo e-mail)
        if User.objects.filter(email=email_txt).exists():
            messages.error(request, "Este e-mail já está cadastrado em outra conta!")
            return render(request, 'registration/cadastro.html')
            
        # 5. Se passou em tudo, cria o usuário com segurança usando a criptografia do Django
        user = User.objects.create_user(
            username=usuario_txt,
            email=email_txt,
            password=senha_txt
        )
        user.save()
        
        # Redireciona o novo jogador para a tela de login
        return redirect('login')
        
    # Se for uma requisição GET, apenas exibe a página limpa
    return render(request, 'registration/cadastro.html')

@login_required
def palpites_extras(request):
    """
    Exibe o Pódio Virtual calculado automaticamente pelo sistema
    baseado nos palpites do Mata-Mata do usuário.
    """
    # Tenta buscar o pódio do usuário
    podium = PalpitePodium.objects.filter(usuario=request.user).first()
    
    return render(request, 'palpites_extras.html', {'podium': podium})


# --- 3. VIEWS ESPECÍFICAS (As rotas chamam estas funções) ---

@login_required
def etapa_16avos(request):
    # Passamos 25% de progresso
    return gerenciar_etapa(request, ['16AVOS'], '16-Avos de Final', 'etapa_oitavas', 25)

@login_required
def etapa_oitavas(request):
    # Passamos 50%
    return gerenciar_etapa(request, ['OITAVAS'], 'Oitavas de Final', 'etapa_quartas', 50)

@login_required
def etapa_quartas(request):
    # Passamos 75%
    return gerenciar_etapa(request, ['QUARTAS'], 'Quartas de Final', 'etapa_semis', 75)

@login_required
def etapa_semis(request):
    # Processa apenas as 2 Semifinais
    # Ao salvar, o sistema calcula os finalistas e manda para a 'etapa_final'
    return gerenciar_etapa(request, ['SEMI'], 'Semi-Finais', 'etapa_final', 90)

@login_required
def etapa_final(request):
    # Processa Disputa de 3º Lugar e a Grande Final
    # Ao salvar aqui, o ciclo fecha e vai para o Bônus/Pódio
    return gerenciar_etapa(request, ['3LUGAR', 'FINAL'], 'Grande Final', 'palpites_extras', 100)


### FUNCOES PARA ACOMPANHAR OS PALPIPTES ###

@login_required
def acompanhar_hub(request):
    """ Exibe a lista de usuários que já finalizaram os palpites (possuem Pódio) """
    # Pega todos os usuários que têm um registro na tabela PalpitePodium
    usuarios_concluidos = User.objects.filter(palpitepodium__isnull=False).distinct()
    
    return render(request, 'acompanhar_hub.html', {'usuarios_concluidos': usuarios_concluidos})

@login_required
def acompanhar_detalhe(request, usuario_id):
    """ Exibe os palpites detalhados de um jogador específico """
    jogador = get_object_or_404(User, id=usuario_id)
    podio = PalpitePodium.objects.filter(usuario=jogador).first()
    
    if not podio:
        return redirect('acompanhar_hub')

    palpites_db = Palpite.objects.filter(usuario=jogador).select_related('partida', 'partida__time_casa', 'partida__time_visitante').order_by('partida__numero_jogo')
    
    classificados_jogador = calcular_classificacao_usuario(jogador)
    
    # === NOVIDADE: PREPARANDO OS DADOS DOS GRUPOS PARA A TELA ===
    letras_grupos = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    resumo_grupos = []
    
    # Separa 1º e 2º de cada grupo
    for letra in letras_grupos:
        resumo_grupos.append({
            'letra': letra,
            'primeiro': classificados_jogador.get(f'1{letra}'),
            'segundo': classificados_jogador.get(f'2{letra}'),
        })
        
    # Separa os 8 melhores terceiros
    melhores_terceiros = []
    for i in range(1, 9):
        time_t = classificados_jogador.get(f'T{i}')
        if time_t:
            melhores_terceiros.append(time_t)
    # ============================================================

    palpites_processados = []
    for p in palpites_db:
        if p.partida.fase == 'GRUPOS':
            tc = p.partida.time_casa
            tv = p.partida.time_visitante
        else:
            tc, tv = resolver_partida_mata_mata(p.partida, classificados_jogador, jogador)
        
        # ADICIONADO: Extrai os IDs reais para o HTML poder comparar
        id_casa_real = tc.id if (tc and hasattr(tc, 'id')) else None
        id_vis_real = tv.id if (tv and hasattr(tv, 'id')) else None

        palpites_processados.append({
            'fase': p.partida.fase, # Enviando o código limpo da fase (ex: '16AVOS')
            'fase_display': p.partida.get_fase_display(),
            'data': p.partida.data_jogo,
            'time_casa': tc.nome if tc else "Indefinido",
            'img_casa': tc.imagem if (tc and tc.imagem) else None,
            'time_vis': tv.nome if tv else "Indefinido",
            'img_vis': tv.imagem if (tv and tv.imagem) else None,
            'gols_casa': p.palpite_casa,
            'gols_vis': p.palpite_visitante,
            
            # NOVAS CHAVES ADICIONADAS PARA O ESPIONAR:
            'id_casa_puro': id_casa_real,
            'id_vis_puro': id_vis_real,
            'vencedor_confronto_id': p.vencedor_confronto_id
        })

    return render(request, 'acompanhar_detalhe.html', {
        'jogador': jogador,
        'podio': podio,
        'resumo_grupos': resumo_grupos,        # <--- Novo item enviado pra tela
        'melhores_terceiros': melhores_terceiros, # <--- Novo item enviado pra tela
        'palpites': palpites_processados
    })