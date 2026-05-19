import os
import random
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from bolao.models import Partida, Palpite, Time
from django.contrib.auth.models import User
from bolao.services import (
    calcular_classificacao_usuario, atualizar_confrontos, 
    calcular_pontos_podium_geral, calcular_pontos_classificacao_grupos, 
    calcular_pontos_confrontos_matamata
)

def simular():
    print("--- INICIANDO TESTE DE INTEGRAÇÃO (MODO TURBO COMPLETO) ---")

    with open('relatorio_simulacao.txt', 'w', encoding='utf-8') as relatorio:
        relatorio.write("🏆 RELATÓRIO DO TESTE DE INTEGRAÇÃO 🏆\n\n")

        # 1. Limpar resultados antigos
        Partida.objects.all().update(gols_casa=None, gols_visitante=None, vencedor_penaltis=None)
        Partida.objects.exclude(fase='GRUPOS').update(time_casa=None, time_visitante=None)
        
        # 2. Simular Fase de Grupos
        print("Preenchendo Fase de Grupos...")
        relatorio.write("--- RESULTADOS REAIS DA FASE DE GRUPOS ---\n")
        jogos_grupos = Partida.objects.filter(fase='GRUPOS').order_by('numero_jogo')
        
        for jogo in jogos_grupos:
            gc, gv = random.randint(0, 3), random.randint(0, 3)
            jogo.gols_casa, jogo.gols_visitante = gc, gv
            jogo.vencedor_penaltis = None
            jogo.save(skip_calc=True) 
            relatorio.write(f"Jogo {jogo.numero_jogo}: {jogo.time_casa.nome} {gc} x {gv} {jogo.time_visitante.nome}\n")

        # Alimenta a primeira fase do Mata-Mata (16AVOS)
        atualizar_confrontos()

        relatorio.write("\n--- QUEM PASSOU DE FASE (CLASSIFICAÇÃO REAL) ---\n")
        classificacao_oficial = calcular_classificacao_usuario(user=None)
        for chave, time in classificacao_oficial.items():
            relatorio.write(f"Vaga {chave}: {time.nome} (Grupo {time.grupo})\n")

        # 3. Simular Mata-Mata FASE POR FASE
        print("Preenchendo Mata-Mata por etapas...")
        relatorio.write("\n--- RESULTADOS REAIS DO MATA-MATA ---\n")
        
        fases_mata_mata = ['16AVOS', 'OITAVAS', 'QUARTAS', 'SEMI', '3LUGAR', 'FINAL']
        
        for fase_nome in fases_mata_mata:
            # Busca os jogos da fase atual (que já foram preenchidos pela fase anterior)
            jogos_fase = Partida.objects.filter(fase=fase_nome).order_by('numero_jogo')
            
            for jogo in jogos_fase:
                if not jogo.time_casa or not jogo.time_visitante: 
                    continue

                gc, gv = random.randint(0, 3), random.randint(0, 3)
                jogo.gols_casa, jogo.gols_visitante = gc, gv
                
                if gc == gv:
                    jogo.vencedor_penaltis = random.choice([jogo.time_casa, jogo.time_visitante])
                    vencedor_str = f" (Vitória nos pênaltis: {jogo.vencedor_penaltis.nome})"
                else:
                    jogo.vencedor_penaltis = None
                    vencedor_str = ""
                
                jogo.save(skip_calc=True) 
                relatorio.write(f"Jogo {jogo.numero_jogo} ({jogo.get_fase_display()}): {jogo.time_casa.nome} {gc} x {gv} {jogo.time_visitante.nome}{vencedor_str}\n")
            
            # 🔴 A CHAVE DO SUCESSO: Avança os vencedores para a PRÓXIMA fase do mata-mata
            atualizar_confrontos()

        # 4. CALCULAR PONTOS REAIS DE CONCURSO (RODA APENAS 1 VEZ NO FINAL)
        print("Calculando notas de todos os usuários (Aguarde)...")
        relatorio.write("\n--- PONTUAÇÃO FINAL APLICADA PELO BANCO DE DADOS ---\n")
        
        # A) Calcula os pontos dos jogos (Palpites)
        for p in Palpite.objects.all():
            p.calcular_pontuacao()
            p.save()
            
        # B) Calcula as regras pesadas (Grupos, Pódio, Confrontos Completos/Parciais)
        calcular_pontos_podium_geral()
        calcular_pontos_classificacao_grupos()
        calcular_pontos_confrontos_matamata()

        # 5. Imprime o placar final oficial somado
        for usuario in User.objects.all():
            pts_jogos = sum([p.pontos for p in Palpite.objects.filter(usuario=usuario)])
            podio = usuario.palpitepodium.total_pontos() if hasattr(usuario, 'palpitepodium') else 0
            
            relatorio.write(f"Usuário: {usuario.username} -> Total: {pts_jogos + podio} Pts\n")

    print("✅ Simulação completa a jato concluída! Abra 'relatorio_simulacao.txt'.")

if __name__ == "__main__":
    simular()