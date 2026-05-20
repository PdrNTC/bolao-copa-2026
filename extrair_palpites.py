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
    print("--- EXTRAINDO PALPITES DETALHADOS DOS USUÁRIOS ---")

    with open('relatorio_palpites.txt', 'w', encoding='utf-8') as f:
        f.write("📊 RELATÓRIO DETALHADO DE PALPITES DOS JOGADORES 📊\n")
        f.write("Compare este arquivo com o 'relatorio_simulacao.txt'\n\n")

        # Calcula o Gabarito Oficial uma única vez
        classificacao_real = calcular_classificacao_usuario(user=None)
        letras_grupos = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']

        for username in lista_usernames:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                print(f"⚠️ Usuário '{username}' não encontrado. Pulando...")
                continue

            f.write("=================================================================\n")
            f.write(f"👤 JOGADOR: {user.username.upper()}\n")
            f.write("=================================================================\n")

            # --- BUSCA DE DADOS ---
            palpites = Palpite.objects.filter(usuario=user).select_related('partida').order_by('partida__numero_jogo')
            classificados_user = calcular_classificacao_usuario(user)
            podio = PalpitePodium.objects.filter(usuario=user).first()
            extras = PalpiteExtra.objects.filter(usuario=user)

            # --- SEPARAÇÃO DE PONTOS ---
            total_jogos = sum([p.pontos for p in palpites if p.pontos])
            total_grupos = podio.pontos_fase_grupos if podio else 0
            total_confrontos = podio.pontos_confrontos if podio else 0
            total_podio_puro = (podio.pontos_campeao + podio.pontos_vice + podio.pontos_terceiro + podio.pontos_quarto) if podio else 0
            total_extras = sum([e.pontos_ganhos for e in extras if e.pontos_ganhos])
            
            total_geral = total_jogos + total_grupos + total_confrontos + total_podio_puro + total_extras

            f.write(f"🏆 PONTUAÇÃO GERAL: {total_geral} Pts\n")
            f.write(f"   ├─ Pontos em Placares (Jogos): {total_jogos} Pts\n")
            f.write(f"   ├─ Pontos em Classificação dos Grupos: {total_grupos} Pts\n")
            f.write(f"   ├─ Pontos em Confrontos (Mata-Mata): {total_confrontos} Pts\n")
            f.write(f"   ├─ Pontos no Pódio (1º ao 4º): {total_podio_puro} Pts\n")
            f.write(f"   └─ Pontos Extras (Perguntas): {total_extras} Pts\n\n")

            # --- DETALHE 1: CLASSIFICAÇÃO DOS GRUPOS ---
            f.write("--- 📊 CLASSIFICAÇÃO DOS GRUPOS (APOSTADO vs REAL) ---\n")
            for letra in letras_grupos:
                c1_user = classificados_user.get(f'1{letra}')
                c2_user = classificados_user.get(f'2{letra}')
                c1_real = classificacao_real.get(f'1{letra}')
                c2_real = classificacao_real.get(f'2{letra}')

                nome_c1_user = c1_user.nome if c1_user else "N/A"
                nome_c2_user = c2_user.nome if c2_user else "N/A"
                nome_c1_real = c1_real.nome if c1_real else "TBD"
                nome_c2_real = c2_real.nome if c2_real else "TBD"

                pts_grupo = 0
                if c1_real and c2_real and c1_user and c2_user:
                    if c1_user == c1_real and c2_user == c2_real: pts_grupo = 75
                    elif c1_user == c2_real and c2_user == c1_real: pts_grupo = 40
                    elif c1_user == c1_real: pts_grupo = 55
                    elif c2_user == c2_real: pts_grupo = 50

                f.write(f"Grupo {letra}:\n")
                f.write(f"  Aposta -> 1º: {nome_c1_user} | 2º: {nome_c2_user}\n")
                f.write(f"  Real   -> 1º: {nome_c1_real} | 2º: {nome_c2_real}  => Ganhou: {pts_grupo} pts\n\n")

            # --- DETALHE 2: FASE DE GRUPOS (PLACAR) ---
            f.write("--- ⚽ FASE DE GRUPOS (PONTOS DE PLACAR) ---\n")
            for p in palpites.filter(partida__fase='GRUPOS'):
                tc = p.partida.time_casa.nome if p.partida.time_casa else "TBD"
                tv = p.partida.time_visitante.nome if p.partida.time_visitante else "TBD"
                real_c = p.partida.gols_casa if p.partida.gols_casa is not None else "-"
                real_v = p.partida.gols_visitante if p.partida.gols_visitante is not None else "-"
                f.write(f"Jogo {p.partida.numero_jogo}: {tc} [{p.palpite_casa} x {p.palpite_visitante}] {tv}  -->  (Real: {real_c}x{real_v}) | Ganhou: {p.pontos} pts\n")

            # --- DETALHE 3: MATA-MATA (PLACAR E CONFRONTOS) ---
            f.write("\n--- ⚔️ MATA-MATA (PONTOS DE PLACAR E CONFRONTOS) ---\n")
            f.write("Nota: 'Pts Placar' = Acerto de gols/tendência. 'Pts Confronto' = Acertar quem jogaria a partida.\n\n")
            
            jogos_reais_mata_mata = Partida.objects.exclude(fase='GRUPOS').filter(time_casa__isnull=False, time_visitante__isnull=False)
            
            tabela_pontos_confronto = {
                '16AVOS': {'parcial': 0, 'completo': 0},
                'OITAVAS': {'parcial': 100, 'completo': 150},
                'QUARTAS': {'parcial': 175, 'completo': 200},
                'SEMI': {'parcial': 225, 'completo': 250},
                '3LUGAR': {'parcial': 275, 'completo': 300},
                'FINAL': {'parcial': 325, 'completo': 350},
            }

            for p in palpites.exclude(partida__fase='GRUPOS'):
                # Descobre os times que o usuário gerou para essa chave
                tc_virtual, tv_virtual = resolver_partida_mata_mata(p.partida, classificados_user, user)
                nome_c_user = tc_virtual.nome if tc_virtual else f"({p.partida.referencia_casa})"
                nome_v_user = tv_virtual.nome if tv_virtual else f"({p.partida.referencia_visitante})"

                # Pega os times reais que jogaram
                jogo_real = jogos_reais_mata_mata.filter(id=p.partida.id).first()
                if jogo_real:
                    nome_c_real = jogo_real.time_casa.nome
                    nome_v_real = jogo_real.time_visitante.nome
                    real_c_gols = jogo_real.gols_casa if jogo_real.gols_casa is not None else "-"
                    real_v_gols = jogo_real.gols_visitante if jogo_real.gols_visitante is not None else "-"
                    
                    # Calcula pontos de confronto on-the-fly para exibir no relatório
                    pts_confronto = 0
                    times_reais = {jogo_real.time_casa.id, jogo_real.time_visitante.id}
                    times_user = {tc_virtual.id, tv_virtual.id} if tc_virtual and tv_virtual else set()
                    
                    acertos = len(times_reais.intersection(times_user))
                    fase = p.partida.fase
                    if acertos == 2: pts_confronto = tabela_pontos_confronto[fase]['completo']
                    elif acertos == 1: pts_confronto = tabela_pontos_confronto[fase]['parcial']
                else:
                    nome_c_real, nome_v_real, real_c_gols, real_v_gols, pts_confronto = "TBD", "TBD", "-", "-", 0

                penaltis_str = ""
                if p.palpite_casa == p.palpite_visitante and p.vencedor_confronto:
                    penaltis_str = f" (Avança: {p.vencedor_confronto.nome})"

                f.write(f"Jogo {p.partida.numero_jogo} ({p.partida.get_fase_display()}):\n")
                f.write(f"  Aposta -> Confronto: {nome_c_user} vs {nome_v_user} | Placar: [{p.palpite_casa} x {p.palpite_visitante}]{penaltis_str}\n")
                f.write(f"  Real   -> Confronto: {nome_c_real} vs {nome_v_real} | Placar: ({real_c_gols} x {real_v_gols})\n")
                f.write(f"  => Ganhou: {p.pontos} Pts (Placar) + {pts_confronto} Pts (Confronto)\n\n")

            # --- DETALHE 4: PÓDIO ---
            if podio:
                f.write("--- 🏅 PÓDIO APOSTADO E PONTUAÇÃO ---\n")
                f.write(f"🥇 Campeão: {podio.campeao.nome if podio.campeao else 'N/A'} | Ganhou: {podio.pontos_campeao} pts\n")
                f.write(f"🥈 Vice: {podio.vice.nome if podio.vice else 'N/A'} | Ganhou: {podio.pontos_vice} pts\n")
                f.write(f"🥉 3º Lugar: {podio.terceiro.nome if podio.terceiro else 'N/A'} | Ganhou: {podio.pontos_terceiro} pts\n")
                f.write(f"🏅 4º Lugar: {podio.quarto.nome if podio.quarto else 'N/A'} | Ganhou: {podio.pontos_quarto} pts\n")
            
            f.write("\n\n")

    print("✅ Relatório detalhado gerado com sucesso! Abra 'relatorio_palpites.txt'.")

if __name__ == "__main__":
    usuarios_para_analisar = ['TestePontos', 'pedro', 'joao', 'teste'] 
    gerar_relatorio_usuarios(usuarios_para_analisar)