from bolao.models import Time

mapa_bandeiras = {
    'México': 'mx', 'África do Sul': 'za', 'Coreia do Sul': 'kr', 'República Tcheca': 'cz',
    'Canadá': 'ca', 'Bósnia e Herzegovina': 'ba', 'Catar': 'qa', 'Suíça': 'ch',
    'Brasil': 'br', 'Marrocos': 'ma', 'Haiti': 'ht', 'Escócia': 'gb-sct',
    'Estados Unidos': 'us', 'Paraguai': 'py', 'Austrália': 'au', 'Turquia': 'tr',
    'Alemanha': 'de', 'Curaçau': 'cw', 'Costa do Marfim': 'ci', 'Equador': 'ec',
    'Holanda': 'nl', 'Japão': 'jp', 'Suécia': 'se', 'Tunísia': 'tn',
    'Bélgica': 'be', 'Egito': 'eg', 'Irã': 'ir', 'Nova Zelândia': 'nz',
    'Espanha': 'es', 'Cabo Verde': 'cv', 'Arábia Saudita': 'sa', 'Uruguai': 'uy',
    'França': 'fr', 'Senegal': 'sn', 'Iraque': 'iq', 'Noruega': 'no',
    'Argentina': 'ar', 'Argélia': 'dz', 'Áustria': 'at', 'Jordânia': 'jo',
    'Portugal': 'pt', 'RD Congo': 'cd', 'Uzbequistão': 'uz', 'Colômbia': 'co',
    'Inglaterra': 'gb-eng', 'Croácia': 'hr', 'Gana': 'gh', 'Panamá': 'pa'
}

for nome, sigla in mapa_bandeiras.items():
    url_imagem = f"https://flagcdn.com/w40/{sigla}.png"
    Time.objects.filter(nome=nome).update(imagem=url_imagem)

print("✅ Bandeiras vinculadas com sucesso!")