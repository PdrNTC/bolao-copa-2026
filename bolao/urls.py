from django.urls import path
from . import views

urlpatterns = [
    # Página inicial é o Ranking
    path('', views.ranking, name='ranking'),
    # "Jogos" agora é a Fase de Grupos
    path('palpites/', views.meus_palpites, name='palpites'),
    # Novas rotas separadas por etapa
    path('matamata/16avos/', views.etapa_16avos, name='etapa_16avos'),
    path('matamata/oitavas/', views.etapa_oitavas, name='etapa_oitavas'),
    path('matamata/quartas/', views.etapa_quartas, name='etapa_quartas'),
    path('matamata/semis/', views.etapa_semis, name='etapa_semis'),
    path('matamata/final/', views.etapa_final, name='etapa_final'),
    # Bônus / Perguntas Extras
    path('extras/', views.palpites_extras, name='palpites_extras'),
    # Cadastro
    path('cadastro/', views.cadastro, name='cadastro'),

    # Novas rotas para Acompanhar Palpites
    path('acompanhar/', views.acompanhar_hub, name='acompanhar_hub'),
    path('acompanhar/<int:usuario_id>/', views.acompanhar_detalhe, name='acompanhar_detalhe'),
]