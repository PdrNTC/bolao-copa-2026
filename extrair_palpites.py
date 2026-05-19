import os
import django

# Configuração do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from bolao.models import Palpite, PalpitePodium, Partida, PalpiteExtra
from django.contrib.auth.models import User
from bolao.services import calcular_classificacao_usuario
from bolao.utils import resolver_partida_mata_mata

def gerar_relatorio_usuarios(lista_usernames):
    print("--- EXTRAINDO PALPITES DOS USUÁRIOS ---")

    with open('relatorio_palpites.txt', 'w', encoding='utf-8') as f:
        f.write("📊 RELATÓRIO DE PALPITES DOS JOGADORES 📊\n")
        f.write("Compare este arquivo com o 'relatorio_simulacao.txt'\n\n")

        for username in lista_usernames:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                print(f"⚠️ Usuário '{username}' não encontrado. Pulando...")
                continue

            f.write("=================================================================\n")
            f.write(f"👤 JOGADOR: {user.username.upper()}\n")
            f.write("=================================================================\n")

            # Busca Palpites de Jogos
            palpites = Palpite.objects.filter(usuario=user).select_related('partida').order_by('partida__numero_jogo')
            total_jogos = sum([p.pontos for p in palpites if p.pontos])
            
            # Busca Pódio
            podio = PalpitePodium.objects.filter(usuario=user).first()
            total_podio = podio.total_pontos() if podio else 0
            
            # Busca Pontos Extras (1º e 2º colocados / Artilheiro, etc)
            extras = PalpiteExtra.objects.filter(usuario=user)
            total_extras = sum([e.pontos_ganhos for e in extras if e.pontos_ganhos])
            
            # Calcula o Total Geral Absoluto
            total_geral = total_jogos + total_podio + total_extras

            f.write(f"🏆 PONTUAÇÃO GERAL: {total_geral} Pts\n")
            f.write(f"   ├─ Pontos em Jogos: {total_jogos} Pts\n")
            f.write(f"   ├─ Pontos em Pódio: {total_podio} Pts\n")
            f.write(f"   └─ Pontos Extras : {total_extras} Pts\n\n")

            # --- FASE DE GRUPOS ---
            f.write("--- FASE DE GRUPOS ---\n")
            for p in palpites.filter(partida__fase='GRUPOS'):
                tc = p.partida.time_casa.nome if p.partida.time_casa else "TBD"
                tv = p.partida.time_visitante.nome if p.partida.time_visitante else "TBD"
                real_c = p.partida.gols_casa if p.partida.gols_casa is not None else "-"
                real_v = p.partida.gols_visitante if p.partida.gols_visitante is not None else "-"
                f.write(f"Jogo {p.partida.numero_jogo}: {tc} [{p.palpite_casa} x {p.palpite_visitante}] {tv}  -->  (Real: {real_c}x{real_v}) | Ganhou: {p.pontos} pts\n")

            # --- MATA-MATA ---
            f.write("\n--- MATA-MATA (Caminho Virtual do Jogador) ---\n")
            classificados_user = calcular_classificacao_usuario(user)
            for p in palpites.exclude(partida__fase='GRUPOS'):
                tc_virtual, tv_virtual = resolver_partida_mata_mata(p.partida, classificados_user, user)
                nome_c = tc_virtual.nome if tc_virtual else f"({p.partida.referencia_casa})"
                nome_v = tv_virtual.nome if tv_virtual else f"({p.partida.referencia_visitante})"
                real_c = p.partida.gols_casa if p.partida.gols_casa is not None else "-"
                real_v = p.partida.gols_visitante if p.partida.gols_visitante is not None else "-"
                
                penaltis_str = ""
                if p.palpite_casa == p.palpite_visitante and p.vencedor_confronto:
                    penaltis_str = f" (Passa: {p.vencedor_confronto.nome})"

                f.write(f"Jogo {p.partida.numero_jogo} ({p.partida.get_fase_display()}): {nome_c} [{p.palpite_casa} x {p.palpite_visitante}] {nome_v}{penaltis_str}  -->  (Real: {real_c}x{real_v}) | Ganhou: {p.pontos} pts\n")

            # --- PÓDIO ---
            if podio:
                f.write("\n--- PÓDIO APOSTADO E PONTUAÇÃO ---\n")
                f.write(f"🥇 Campeão: {podio.campeao.nome if podio.campeao else 'N/A'} | Ganhou: {podio.pontos_campeao} pts\n")
                f.write(f"🥈 Vice: {podio.vice.nome if podio.vice else 'N/A'} | Ganhou: {podio.pontos_vice} pts\n")
                f.write(f"🥉 3º Lugar: {podio.terceiro.nome if podio.terceiro else 'N/A'} | Ganhou: {podio.pontos_terceiro} pts\n")
                f.write(f"🏅 4º Lugar: {podio.quarto.nome if podio.quarto else 'N/A'} | Ganhou: {podio.pontos_quarto} pts\n")
            
            # --- PERGUNTAS EXTRAS (1º e 2º Colocados, etc) ---
            if extras.exists():
                f.write("\n--- PONTOS EXTRAS APOSTADOS ---\n")
                for e in extras:
                    f.write(f"Pergunta: {e.pergunta.titulo} | Resposta: {e.resposta_usuario} | Ganhou: {e.pontos_ganhos} pts\n")

            f.write("\n\n")

    print("✅ Relatório de palpites gerado com sucesso! Abra 'relatorio_palpites.txt'.")

if __name__ == "__main__":
    usuarios_para_analisar = ['TestePontos', 'pedro'] 
    gerar_relatorio_usuarios(usuarios_para_analisar)