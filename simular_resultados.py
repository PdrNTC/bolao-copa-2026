import os
import random
import django

# Configuração do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from bolao.models import Partida, Palpite, Time
from django.contrib.auth.models import User
from bolao.services import resolver_time_real, calcular_classificacao_grupo_real

def simular():
    print("--- INICIANDO SIMULAÇÃO E GERANDO RELATÓRIO ---")

    # Prepara o arquivo de relatório
    with open('relatorio_simulacao.txt', 'w', encoding='utf-8') as relatorio:
        relatorio.write("🏆 RELATÓRIO DE GABARITO DA SIMULAÇÃO 🏆\n")
        relatorio.write("Use este arquivo para conferir se os pontos foram calculados corretamente.\n\n")

        # 1. Limpar resultados antigos
        Partida.objects.all().update(gols_casa=None, gols_visitante=None)
        
        # Limpa os times apenas dos jogos de mata-mata (preservando os times da fase de grupos)
        Partida.objects.exclude(fase='GRUPOS').update(time_casa=None, time_visitante=None)
        
        # 2. Simular Fase de Grupos
        relatorio.write("--- RESULTADOS DA FASE DE GRUPOS ---\n")
        jogos_grupos = Partida.objects.filter(fase='GRUPOS').order_by('numero_jogo')
        
        for jogo in jogos_grupos:
            gc = random.randint(0, 4)
            gv = random.randint(0, 4)
            jogo.gols_casa = gc
            jogo.gols_visitante = gv
            jogo.save()
            
            linha = f"Jogo {jogo.numero_jogo}: {jogo.time_casa.nome} {gc} x {gv} {jogo.time_visitante.nome}\n"
            relatorio.write(linha)

        # 3. Resolver Times do Mata-Mata
        classificacao_real = {}
        letras_grupos = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
        for letra in letras_grupos:
            tabela = calcular_classificacao_grupo_real(letra)
            if len(tabela) >= 1: classificacao_real[f'1{letra}'] = tabela[0]['time']
            if len(tabela) >= 2: classificacao_real[f'2{letra}'] = tabela[1]['time']
            if len(tabela) >= 3: classificacao_real[f'T{letras_grupos.index(letra)+1}'] = tabela[2]['time']

        # 4. Simular Mata-Mata
        relatorio.write("\n--- RESULTADOS DO MATA-MATA ---\n")
        fases_mata_mata = ['16AVOS', 'OITAVAS', 'QUARTAS', 'SEMI', '3LUGAR', 'FINAL']
        
        for fase_nome in fases_mata_mata:
            jogos_fase = Partida.objects.filter(fase=fase_nome).order_by('numero_jogo')
            for jogo in jogos_fase:
                time_c = resolver_time_real(jogo.referencia_casa, classificacao_real)
                time_v = resolver_time_real(jogo.referencia_visitante, classificacao_real)
                
                jogo.time_casa = time_c
                jogo.time_visitante = time_v
                
                gc = random.randint(0, 4)
                gv = random.randint(0, 4)
                if gc == gv: gc += 1 # Evita empate
                
                jogo.gols_casa = gc
                jogo.gols_visitante = gv
                jogo.save()

                nome_c = time_c.nome if time_c else jogo.referencia_casa
                nome_v = time_v.nome if time_v else jogo.referencia_visitante
                linha = f"Jogo {jogo.numero_jogo} ({jogo.get_fase_display()}): {nome_c} {gc} x {gv} {nome_v}\n"
                relatorio.write(linha)

        # 5. Calcular Pontuação dos Usuários
        relatorio.write("\n--- PONTUAÇÃO FINAL DOS USUÁRIOS ---\n")
        usuarios = User.objects.all()

        for usuario in usuarios:
            total_usuario = 0
            palpites = Palpite.objects.filter(usuario=usuario)
            
            for palpite in palpites:
                pts = 0
                real_casa = palpite.partida.gols_casa
                real_vis = palpite.partida.gols_visitante
                palp_casa = palpite.palpite_casa
                palp_vis = palpite.palpite_visitante

                # Evita erro caso o jogo real ou o palpite estejam vazios
                if real_casa is not None and real_vis is not None and palp_casa is not None and palp_vis is not None:
                    if real_casa == palp_casa and real_vis == palp_vis:
                        pts = 3
                    elif (real_casa > real_vis and palp_casa > palp_vis) or \
                         (real_vis > real_casa and palp_vis > palp_casa) or \
                         (real_casa == real_vis and palp_casa == palp_vis):
                        pts = 1
                
                palpite.pontos = pts
                palpite.save()
                total_usuario += pts
            
            relatorio.write(f"Usuário: {usuario.username} -> Total: {total_usuario} Pts\n")

    print("✅ Simulação concluída! Abra o arquivo 'relatorio_simulacao.txt' para ver o gabarito.")

if __name__ == "__main__":
    simular()