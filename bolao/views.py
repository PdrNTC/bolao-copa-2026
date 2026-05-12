from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

# Importe os novos Models e Utils
from .models import Partida, Palpite, PalpiteExtra, PerguntaExtra, PalpitePodium
# Importa a classificação do services, e o resto do utils
from .services import calcular_classificacao_usuario 
from .utils import resolver_partida_mata_mata, simular_caminho_usuario

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

# --- RANKING ATUALIZADO ---
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
    # Fases que queremos mostrar nessa tela
    fases_finais = ['16AVOS', 'OITAVAS', 'QUARTAS', 'SEMI', '3LUGAR', 'FINAL']
    
    if request.method == 'POST':
        # Busca apenas partidas de mata-mata
        partidas = Partida.objects.filter(fase__in=fases_finais)
        
        for partida in partidas:
            placar_casa = request.POST.get(f'gols_casa_{partida.id}')
            placar_vis = request.POST.get(f'gols_vis_{partida.id}')

            if placar_casa and placar_vis:
                Palpite.objects.update_or_create(
                    usuario=request.user,
                    partida=partida,
                    defaults={
                        'palpite_casa': int(placar_casa),
                        'palpite_visitante': int(placar_vis)
                    }
                )
        
        # O PULO DO GATO:
        # Após salvar os palpites do mata-mata, o sistema roda a simulação
        # para descobrir quem é o Campeão Virtual desse usuário e salvar no Pódio.
        simular_caminho_usuario(request.user)
        
        return redirect('ranking')

    else:
        # GET: Preparar a visualização inteligente
        
        # 1. Calcula toda a classificação dos grupos desse usuário
        classificados = calcular_classificacao_usuario(request.user)
        
        partidas = Partida.objects.filter(fase__in=fases_finais).order_by('numero_jogo')
        lista_jogos = []

        for partida in partidas:
            # Descobre quem joga (Brasil? França?) baseado nos palpites anteriores
            t_casa, t_vis = resolver_partida_mata_mata(partida, classificados, request.user)
            
            palpite = Palpite.objects.filter(usuario=request.user, partida=partida).first()

            lista_jogos.append({
                'partida': partida,
                # Se o sistema conseguiu calcular o time, mostra o nome e bandeira.
                # Se não (ex: usuário não preencheu os grupos), mostra a referência (ex: "1º do A")
                'time_casa_visual': t_casa if t_casa else {'nome': f'({partida.referencia_casa})', 'imagem': ''},
                'time_vis_visual': t_vis if t_vis else {'nome': f'({partida.referencia_visitante})', 'imagem': ''},
                'palpite_casa': palpite.palpite_casa if palpite else '',
                'palpite_vis': palpite.palpite_visitante if palpite else ''
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
    aceita 'progresso_val' para controlar a barra de progresso
    """
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
            if gc and gv:
                Palpite.objects.update_or_create(
                    usuario=request.user, partida=partida,
                    defaults={'palpite_casa': int(gc), 'palpite_visitante': int(gv)}
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

            lista_jogos.append({
                'partida': partida,
                'time_casa_visual': t_casa if t_casa else {'nome': formatar_nome(partida.referencia_casa), 'imagem': ''},
                'time_vis_visual': t_vis if t_vis else {'nome': formatar_nome(partida.referencia_visitante), 'imagem': ''},
                'palpite_casa': palpite.palpite_casa if palpite else '',
                'palpite_vis': palpite.palpite_visitante if palpite else ''
            })

        return render(request, 'etapa_matamata.html', {
            'lista_jogos': lista_jogos,
            'titulo': titulo_etapa,
            'ja_preencheu': ja_preencheu_etapa,
            'proxima_url': proxima_url,
            'progresso': progresso_val  # <--- Enviando o valor para o HTML
        })

def cadastro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/cadastro.html', {'form': form})

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
    
    # Se ele não tem pódio, redireciona de volta (segurança)
    if not podio:
        return redirect('acompanhar_hub')

    # Busca todos os palpites do jogador ordenados pelo número do jogo
    palpites_db = Palpite.objects.filter(usuario=jogador).select_related('partida', 'partida__time_casa', 'partida__time_visitante').order_by('partida__numero_jogo')
    
    # Precisamos resolver os times do mata-mata baseado nas escolhas DELE
    classificados_jogador = calcular_classificacao_usuario(jogador)
    
    palpites_processados = []
    for p in palpites_db:
        # SE FOR GRUPOS: Pega o time fixo do banco de dados
        if p.partida.fase == 'GRUPOS':
            tc = p.partida.time_casa
            tv = p.partida.time_visitante
        # SE FOR MATA-MATA: Resolve baseado nos palpites do jogador
        else:
            tc, tv = resolver_partida_mata_mata(p.partida, classificados_jogador, jogador)
        
        palpites_processados.append({
            'fase': p.partida.get_fase_display(),
            'data': p.partida.data_jogo,
            'time_casa': tc.nome if tc else "Indefinido",
            'img_casa': tc.imagem if (tc and tc.imagem) else None,
            'time_vis': tv.nome if tv else "Indefinido",
            'img_vis': tv.imagem if (tv and tv.imagem) else None,
            'gols_casa': p.palpite_casa,
            'gols_vis': p.palpite_visitante,
        })

    return render(request, 'acompanhar_detalhe.html', {
        'jogador': jogador,
        'podio': podio,
        'palpites': palpites_processados
    })