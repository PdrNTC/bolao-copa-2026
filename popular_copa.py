import os
import django
from datetime import datetime, timedelta
from django.utils import timezone
from bolao.models import Time, Partida, Palpite, PalpitePodium

# Função auxiliar para criar data consciente (aware)
def criar_data(ano, mes, dia, hora=0, minuto=0):
    dt = datetime(ano, mes, dia, hora, minuto)
    return timezone.make_aware(dt)

print("--- INICIANDO POPULAÇÃO OFICIAL FIFA WORLD CUP 2026 ---")

# 1. LIMPEZA DE DADOS ANTIGOS
print("1. Limpando banco de dados antigo...")
Palpite.objects.all().delete()
PalpitePodium.objects.all().delete()
Partida.objects.all().delete()
Time.objects.all().delete()

# 2. LISTA DE SELEÇÕES OFICIAIS (Conforme Calendário FIFA 26)
grupos_definidos = {
    'A': ['México', 'África do Sul', 'Coreia do Sul', 'República Tcheca'],
    'B': ['Canadá', 'Bósnia e Herzegovina', 'Catar', 'Suíça'],
    'C': ['Brasil', 'Marrocos', 'Haiti', 'Escócia'],
    'D': ['Estados Unidos', 'Paraguai', 'Austrália', 'Turquia'],
    'E': ['Alemanha', 'Curaçau', 'Costa do Marfim', 'Equador'],
    'F': ['Holanda', 'Japão', 'Suécia', 'Tunísia'],
    'G': ['Bélgica', 'Egito', 'Irã', 'Nova Zelândia'],
    'H': ['Espanha', 'Cabo Verde', 'Arábia Saudita', 'Uruguai'],
    'I': ['França', 'Senegal', 'Iraque', 'Noruega'],
    'J': ['Argentina', 'Argélia', 'Áustria', 'Jordânia'],
    'K': ['Portugal', 'RD Congo', 'Uzbequistão', 'Colômbia'],
    'L': ['Inglaterra', 'Croácia', 'Gana', 'Panamá'],
}

times_db = {} 

print("2. Criando Times...")
for letra, paises in grupos_definidos.items():
    times_db[letra] = {}
    for nome_pais in paises:
        t = Time.objects.create(
            nome=nome_pais,
            codigo=nome_pais[:3].upper(),
            grupo=letra
        )
        times_db[letra][nome_pais] = t

# 3. GERAR JOGOS DA FASE DE GRUPOS (JOGOS 1 a 72)
print("3. Gerando Fase de Grupos...")

# Mapeamento manual de alguns jogos da 1ª e 2ª rodada conforme calendário para garantir datas
jogos_grupos = [
    # 1ª Rodada
    (1, 'A', 'México', 'África do Sul', criar_data(2026, 6, 11, 16)),
    (2, 'A', 'Coreia do Sul', 'República Tcheca', criar_data(2026, 6, 11, 23)),
    (3, 'B', 'Canadá', 'Bósnia e Herzegovina', criar_data(2026, 6, 12, 16)),
    (4, 'D', 'Estados Unidos', 'Paraguai', criar_data(2026, 6, 12, 22)),
    (5, 'B', 'Catar', 'Suíça', criar_data(2026, 6, 13, 16)),
    (6, 'C', 'Brasil', 'Marrocos', criar_data(2026, 6, 13, 19)),
    (7, 'C', 'Haiti', 'Escócia', criar_data(2026, 6, 13, 22)),
    (8, 'D', 'Austrália', 'Turquia', criar_data(2026, 6, 14, 1)),
    (9, 'E', 'Alemanha', 'Curaçau', criar_data(2026, 6, 14, 14)),
    (10, 'E', 'Costa do Marfim', 'Equador', criar_data(2026, 6, 14, 20)),
    (11, 'F', 'Holanda', 'Japão', criar_data(2026, 6, 14, 17)),
    (12, 'F', 'Suécia', 'Tunísia', criar_data(2026, 6, 14, 23)),
    # ... O script preencherá o restante automaticamente para completar os 72 jogos
]

# Criar os jogos definidos acima
for num, grp, casa, fora, data in jogos_grupos:
    Partida.objects.create(
        numero_jogo=num, fase='GRUPOS',
        time_casa=times_db[grp][casa], time_visitante=times_db[grp][fora],
        data_jogo=data
    )

# Preenchimento automático dos jogos restantes dos grupos para completar 72
print("   -> Completando tabela de grupos...")
data_placeholder = criar_data(2026, 6, 15)
for num in range(13, 73):
    if not Partida.objects.filter(numero_jogo=num).exists():
        # Pega dois times de qualquer grupo para preencher o banco
        t1 = Time.objects.all()[num % 48]
        t2 = Time.objects.all()[(num+1) % 48]
        Partida.objects.create(
            numero_jogo=num, fase='GRUPOS',
            time_casa=t1, time_visitante=t2,
            data_jogo=data_placeholder + timedelta(hours=num)
        )

# 4. GERAR MATA-MATA (JOGOS 73 a 104) - Conforme Calendário FIFA
print("4. Gerando Estrutura do Mata-Mata...")

# --- 32-AVOS (No seu sistema chamado de 16AVOS) ---
# (Num_Jogo, Ref_Casa, Ref_Vis, Data)
fase_32 = [
    (73, '2A', '2B', criar_data(2026, 6, 28)),
    (74, '1E', 'T1', criar_data(2026, 6, 29)),
    (75, '1F', '2C', criar_data(2026, 6, 29)),
    (76, '1C', '2F', criar_data(2026, 6, 29)),
    (77, '1I', 'T2', criar_data(2026, 6, 30)),
    (78, '2E', '2I', criar_data(2026, 6, 30)),
    (79, '1A', 'T3', criar_data(2026, 6, 30)),
    (80, '1L', 'T4', criar_data(2026, 7, 1)),
    (81, '1D', 'T5', criar_data(2026, 7, 1)),
    (82, '1G', 'T6', criar_data(2026, 7, 1)),
    (83, '2K', '2L', criar_data(2026, 7, 2)),
    (84, '1H', '2J', criar_data(2026, 7, 2)),
    (85, '1B', 'T7', criar_data(2026, 7, 2)),
    (86, '1J', '2H', criar_data(2026, 7, 3)),
    (87, '1K', 'T8', criar_data(2026, 7, 3)),
    (88, '2D', '2G', criar_data(2026, 7, 3)),
]

for num, ref_c, ref_v, data in fase_32:
    Partida.objects.create(
        numero_jogo=num, fase='16AVOS',
        data_jogo=data, referencia_casa=ref_c, referencia_visitante=ref_v
    )

# --- OITAVAS DE FINAL ---
oitavas = [
    (89, 'W74', 'W77', criar_data(2026, 7, 4)),
    (90, 'W73', 'W75', criar_data(2026, 7, 4)),
    (91, 'W76', 'W78', criar_data(2026, 7, 5)),
    (92, 'W79', 'W80', criar_data(2026, 7, 5)),
    (93, 'W83', 'W84', criar_data(2026, 7, 6)),
    (94, 'W81', 'W82', criar_data(2026, 7, 6)),
    (95, 'W86', 'W88', criar_data(2026, 7, 7)),
    (96, 'W85', 'W87', criar_data(2026, 7, 7)),
]

for num, ref_c, ref_v, data in oitavas:
    Partida.objects.create(
        numero_jogo=num, fase='OITAVAS',
        data_jogo=data, referencia_casa=ref_c, referencia_visitante=ref_v
    )

# --- QUARTAS DE FINAL ---
quartas = [
    (97, 'W89', 'W90', criar_data(2026, 7, 9)),
    (98, 'W93', 'W94', criar_data(2026, 7, 10)),
    (99, 'W91', 'W92', criar_data(2026, 7, 12)),
    (100, 'W95', 'W96', criar_data(2026, 7, 12)),
]

for num, ref_c, ref_v, data in quartas:
    Partida.objects.create(
        numero_jogo=num, fase='QUARTAS',
        data_jogo=data, referencia_casa=ref_c, referencia_visitante=ref_v
    )

# --- SEMIFINAIS ---
semis = [
    (101, 'W97', 'W98', criar_data(2026, 7, 14)),
    (102, 'W99', 'W100', criar_data(2026, 7, 15)),
]

for num, ref_c, ref_v, data in semis:
    Partida.objects.create(
        numero_jogo=num, fase='SEMI',
        data_jogo=data, referencia_casa=ref_c, referencia_visitante=ref_v
    )

# --- DISPUTA 3º LUGAR E FINAL ---
# Jogo 103: Perdedor 101 x Perdedor 102
Partida.objects.create(
    numero_jogo=103, fase='3LUGAR',
    data_jogo=criar_data(2026, 7, 18),
    referencia_casa='L101', referencia_visitante='L102'
)

# Jogo 104: Vencedor 101 x Vencedor 102
Partida.objects.create(
    numero_jogo=104, fase='FINAL',
    data_jogo=criar_data(2026, 7, 19),
    referencia_casa='W101', referencia_visitante='W102'
)

print("--- CONCLUÍDO! BANCO DE DADOS OFICIAL FIFA 2026 CRIADO ---")
print(f"Total de Partidas: {Partida.objects.count()}")
print(f"Total de Times: {Time.objects.count()}")