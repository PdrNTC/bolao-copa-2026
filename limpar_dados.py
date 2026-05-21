import os
import django

# 1. AJUSTADO PARA O SEU DIRETÓRIO CORRETO ('setup.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

# 2. LIGA O MOTOR DO DJANGO
django.setup()

# 3. IMPORTAÇÃO DOS MODELOS DO DJANGO LIBERADA
from django.contrib.auth.models import User

print("\n==================================================")
print("   💥 INICIANDO LIMPEZA DE DADOS DE TESTE 💥")
print("==================================================")

# Filtra usuários comuns (ignora admins)
usuarios_teste = User.objects.filter(is_superuser=False)
quantidade = usuarios_teste.count()

if quantidade > 0:
    print(f"🗑️  Apagando {quantidade} usuários de teste e todos os seus palpites/pódios...")
    usuarios_teste.delete()
else:
    print("ℹ️  Nenhum usuário comum encontrado para apagar.")

# Reseta a pontuação dos administradores
admins = User.objects.filter(is_superuser=True)
for admin in admins:
    admin.total_pontos = 0
    admin.save()
print("✨ Pontuação de todos os administradores zerada com sucesso!")

print("==================================================")
print(" ✅ BANCO LIMPO E PRONTO PARA O INÍCIO OFICIAL!")
print("==================================================\n")