import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from datetime import timezone
from bolao.models import Partida, Time, Palpite, PalpitePodium

def dt_br(ano, mes, dia, hora, minuto):
    # Retorna o datetime correto convertido para UTC (Django armazena em UTC)
    # Como o fuso de Brasília é UTC-3, somamos 3 horas ao horário de Brasília para achar o UTC.
    tz_br = datetime.timezone(datetime.timedelta(hours=-3))
    dt_local = datetime.datetime(ano, mes, dia, hora, minuto, tzinfo=tz_br)
    return dt_local.astimezone(timezone.utc)

def recriar_jogos():
    print("🧹 Apagando jogos antigos e palpites...")
    Palpite.objects.all().delete()
    PalpitePodium.objects.all().delete()
    Partida.objects.all().delete()

    print("⚽ Criando a Fase de Grupos Oficial com as Datas Reais da FIFA...")
    
    # Mapeamento completo cronológico da Fase de Grupos (Casa, Visitante, Grupo, Data/Hora em Brasília)
    jogos_grupos = [
        # --- 1ª RODADA ---
        ("México", "África do Sul", "A", dt_br(2026, 6, 11, 16, 0)),
        ("Coreia do Sul", "República Tcheca", "A", dt_br(2026, 6, 11, 23, 0)),
        ("Canadá", "Bósnia e Herzegovina", "B", dt_br(2026, 6, 12, 16, 0)),
        ("Estados Unidos", "Paraguai", "D", dt_br(2026, 6, 12, 22, 0)),
        ("Catar", "Suíça", "B", dt_br(2026, 6, 13, 16, 0)),
        ("Brasil", "Marrocos", "C", dt_br(2026, 6, 13, 19, 0)),
        ("Haiti", "Escócia", "C", dt_br(2026, 6, 13, 22, 0)),
        ("Austrália", "Turquia", "D", dt_br(2026, 6, 14, 1, 0)), # Madrugada no BR
        ("Alemanha", "Curaçau", "E", dt_br(2026, 6, 14, 14, 0)),
        ("Holanda", "Japão", "F", dt_br(2026, 6, 14, 17, 0)),
        ("Costa do Marfim", "Equador", "E", dt_br(2026, 6, 14, 20, 0)),
        ("Suécia", "Tunísia", "F", dt_br(2026, 6, 14, 23, 0)),
        ("Espanha", "Cabo Verde", "H", dt_br(2026, 6, 15, 13, 0)),
        ("Bélgica", "Egito", "G", dt_br(2026, 6, 15, 16, 0)),
        ("Arábia Saudita", "Uruguai", "H", dt_br(2026, 6, 15, 19, 0)),
        ("Irã", "Nova Zelândia", "G", dt_br(2026, 6, 15, 22, 0)),
        ("França", "Senegal", "I", dt_br(2026, 6, 16, 16, 0)),
        ("Iraque", "Noruega", "I", dt_br(2026, 6, 16, 19, 0)),
        ("Argentina", "Argélia", "J", dt_br(2026, 6, 16, 22, 0)),
        ("Áustria", "Jordânia", "J", dt_br(2026, 6, 17, 1, 0)), # Madrugada no BR
        ("Portugal", "RD Congo", "K", dt_br(2026, 6, 17, 14, 0)),
        ("Inglaterra", "Croácia", "L", dt_br(2026, 6, 17, 17, 0)),
        ("Gana", "Panamá", "L", dt_br(2026, 6, 17, 20, 0)),
        ("Uzbequistão", "Colômbia", "K", dt_br(2026, 6, 17, 21, 0)),

        # --- 2ª RODADA ---
        ("República Tcheca", "África do Sul", "A", dt_br(2026, 6, 18, 13, 0)),
        ("Suíça", "Bósnia e Herzegovina", "B", dt_br(2026, 6, 18, 16, 0)),
        ("Canadá", "Catar", "B", dt_br(2026, 6, 18, 19, 0)),
        ("México", "Coreia do Sul", "A", dt_br(2026, 6, 18, 22, 0)),
        ("Estados Unidos", "Austrália", "D", dt_br(2026, 6, 19, 16, 0)),
        ("Escócia", "Marrocos", "C", dt_br(2026, 6, 19, 19, 0)),
        ("Brasil", "Haiti", "C", dt_br(2026, 6, 19, 21, 30)),
        ("Turquia", "Paraguai", "D", dt_br(2026, 6, 20, 0, 0)), # Meia-noite BR
        ("Holanda", "Suécia", "F", dt_br(2026, 6, 20, 14, 0)),
        ("Alemanha", "Costa do Marfim", "E", dt_br(2026, 6, 20, 17, 0)),
        ("Equador", "Curaçau", "E", dt_br(2026, 6, 20, 21, 0)),
        ("Tunísia", "Japão", "F", dt_br(2026, 6, 20, 23, 0)),
        ("Espanha", "Arábia Saudita", "H", dt_br(2026, 6, 21, 13, 0)),
        ("Bélgica", "Irã", "G", dt_br(2026, 6, 21, 16, 0)),
        ("Uruguai", "Cabo Verde", "H", dt_br(2026, 6, 21, 19, 0)),
        ("Nova Zelândia", "Egito", "G", dt_br(2026, 6, 21, 22, 0)),
        ("Argentina", "Áustria", "J", dt_br(2026, 6, 22, 14, 0)),
        ("França", "Iraque", "I", dt_br(2026, 6, 22, 18, 0)),
        ("Noruega", "Senegal", "I", dt_br(2026, 6, 22, 21, 0)),
        ("Jordânia", "Argélia", "J", dt_br(2026, 6, 23, 0, 0)), # Meia-noite BR
        ("Portugal", "Uzbequistão", "K", dt_br(2026, 6, 23, 14, 0)),
        ("Inglaterra", "Gana", "L", dt_br(2026, 6, 23, 17, 0)),
        ("Panamá", "Croácia", "L", dt_br(2026, 6, 23, 20, 0)),
        ("Colômbia", "RD Congo", "K", dt_br(2026, 6, 23, 23, 0)),

        # --- 3ª RODADA ---
        ("Suíça", "Canadá", "B", dt_br(2026, 6, 24, 16, 0)),
        ("Bósnia e Herzegovina", "Catar", "B", dt_br(2026, 6, 24, 16, 0)),
        ("Escócia", "Brasil", "C", dt_br(2026, 6, 24, 19, 0)),
        ("Marrocos", "Haiti", "C", dt_br(2026, 6, 24, 19, 0)),
        ("República Tcheca", "México", "A", dt_br(2026, 6, 24, 22, 0)),
        ("África do Sul", "Coreia do Sul", "A", dt_br(2026, 6, 24, 22, 0)),
        ("Equador", "Alemanha", "E", dt_br(2026, 6, 25, 17, 0)),
        ("Curaçau", "Costa do Marfim", "E", dt_br(2026, 6, 25, 17, 0)),
        ("Japão", "Suécia", "F", dt_br(2026, 6, 25, 20, 0)),
        ("Tunísia", "Holanda", "F", dt_br(2026, 6, 25, 20, 0)),
        ("Turquia", "Estados Unidos", "D", dt_br(2026, 6, 25, 23, 0)),
        ("Paraguai", "Austrália", "D", dt_br(2026, 6, 25, 23, 0)),
        ("Noruega", "França", "I", dt_br(2026, 6, 26, 16, 0)),
        ("Senegal", "Iraque", "I", dt_br(2026, 6, 26, 16, 0)),
        ("Cabo Verde", "Arábia Saudita", "H", dt_br(2026, 6, 26, 21, 0)),
        ("Uruguai", "Espanha", "H", dt_br(2026, 6, 26, 21, 0)),
        ("Egito", "Irã", "G", dt_br(2026, 6, 27, 0, 0)), # Meia-noite BR
        ("Nova Zelândia", "Bélgica", "G", dt_br(2026, 6, 27, 0, 0)), # Meia-noite BR
        ("Panamá", "Inglaterra", "L", dt_br(2026, 6, 27, 18, 0)),
        ("Croácia", "Gana", "L", dt_br(2026, 6, 27, 18, 0)),
        ("Colômbia", "Portugal", "K", dt_br(2026, 6, 27, 20, 30)),
        ("RD Congo", "Uzbequistão", "K", dt_br(2026, 6, 27, 20, 30)),
        ("Argélia", "Áustria", "J", dt_br(2026, 6, 27, 23, 0)),
        ("Jordânia", "Argentina", "J", dt_br(2026, 6, 27, 23, 0)),
    ]

    numero_jogo = 1
    for nome_casa, nome_vis, grupo, data_oficial in jogos_grupos:
        time_casa, _ = Time.objects.get_or_create(nome=nome_casa, defaults={'grupo': grupo})
        time_vis, _ = Time.objects.get_or_create(nome=nome_vis, defaults={'grupo': grupo})
        
        if time_casa.grupo != grupo:
            time_casa.grupo = grupo
            time_casa.save()
        if time_vis.grupo != grupo:
            time_vis.grupo = grupo
            time_vis.save()

        Partida.objects.create(
            numero_jogo=numero_jogo,
            fase='GRUPOS',
            time_casa=time_casa,
            time_visitante=time_vis,
            data_jogo=data_oficial
        )
        numero_jogo += 1

    print("⚔️ Criando as Chaves do Mata-Mata com Padrão W/L...")
    
    # Estrutura do Mata-Mata (Número do Jogo, Fase, Ref_Casa, Ref_Visitante, Data_Estipulada)
    # 🔴 AJUSTADO: Mudança de V para W (Winner) e de P para L (Loser)
    mata_mata = [
        # --- 16-AVOS ---
        (73, "16AVOS", "2A", "2B", dt_br(2026, 6, 28, 16, 0)),
        (74, "16AVOS", "1E", "T1", dt_br(2026, 6, 29, 16, 0)),
        (75, "16AVOS", "1F", "2C", dt_br(2026, 6, 29, 16, 0)),
        (76, "16AVOS", "1C", "2F", dt_br(2026, 6, 29, 16, 0)),
        (77, "16AVOS", "1I", "T2", dt_br(2026, 6, 30, 16, 0)),
        (78, "16AVOS", "2E", "2I", dt_br(2026, 6, 30, 16, 0)),
        (79, "16AVOS", "1A", "T3", dt_br(2026, 6, 30, 16, 0)),
        (80, "16AVOS", "1L", "T4", dt_br(2026, 7, 1, 16, 0)),
        (81, "16AVOS", "1D", "T5", dt_br(2026, 7, 1, 16, 0)),
        (82, "16AVOS", "1G", "T6", dt_br(2026, 7, 1, 16, 0)),
        (83, "16AVOS", "2K", "2L", dt_br(2026, 7, 2, 16, 0)),
        (84, "16AVOS", "1H", "2J", dt_br(2026, 7, 2, 16, 0)),
        (85, "16AVOS", "1B", "T7", dt_br(2026, 7, 2, 16, 0)),
        (86, "16AVOS", "1J", "2H", dt_br(2026, 7, 3, 16, 0)),
        (87, "16AVOS", "1K", "T8", dt_br(2026, 7, 3, 16, 0)),
        (88, "16AVOS", "2D", "2G", dt_br(2026, 7, 3, 16, 0)),
        
        # --- OITAVAS ---
        (89, "OITAVAS", "W74", "W77", dt_br(2026, 7, 4, 16, 0)),
        (90, "OITAVAS", "W73", "W75", dt_br(2026, 7, 4, 16, 0)),
        (91, "OITAVAS", "W76", "W78", dt_br(2026, 7, 5, 16, 0)),
        (92, "OITAVAS", "W79", "W80", dt_br(2026, 7, 5, 16, 0)),
        (93, "OITAVAS", "W83", "W84", dt_br(2026, 7, 6, 16, 0)),
        (94, "OITAVAS", "W81", "W82", dt_br(2026, 7, 6, 16, 0)),
        (95, "OITAVAS", "W86", "W88", dt_br(2026, 7, 7, 16, 0)),
        (96, "OITAVAS", "W85", "W87", dt_br(2026, 7, 7, 16, 0)),

        # --- QUARTAS ---
        (97, "QUARTAS", "W89", "W90", dt_br(2026, 7, 9, 16, 0)),
        (98, "QUARTAS", "W93", "W94", dt_br(2026, 7, 10, 16, 0)),
        (99, "QUARTAS", "W91", "W92", dt_br(2026, 7, 12, 16, 0)),
        (100, "QUARTAS", "W95", "W96", dt_br(2026, 7, 12, 16, 0)),

        # --- MEIAS E FINAIS ---
        (101, "SEMI", "W97", "W98", dt_br(2026, 7, 14, 16, 0)),
        (102, "SEMI", "W99", "W100", dt_br(2026, 7, 15, 16, 0)),
        (103, "3LUGAR", "L101", "L102", dt_br(2026, 7, 18, 16, 0)),
        (104, "FINAL", "W101", "W102", dt_br(2026, 7, 19, 16, 0)),
    ]

    for num, fase, ref_c, ref_v, dt_matamata in mata_mata:
        Partida.objects.create(
            numero_jogo=num,
            fase=fase,
            referencia_casa=ref_c,
            referencia_visitante=ref_v,
            data_jogo=dt_matamata
        )

    print("✅ Sucesso Absoluto! A tabela completa da Copa de 2026 está sincronizada no padrão (W/L) com o calendário cronológico da FIFA.")

if __name__ == "__main__":
    recriar_jogos()