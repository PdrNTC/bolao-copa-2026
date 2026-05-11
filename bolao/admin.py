from django.contrib import admin
from .models import Time, Partida, Palpite, PalpitePodium, PerguntaExtra, PalpiteExtra

@admin.register(Time)
class TimeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'grupo')
    list_filter = ('grupo',)

@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    # REMOVI 'grupo' DO LIST_FILTER ABAIXO
    list_display = ('numero_jogo', 'fase', '__str__', 'data_jogo', 'gols_casa', 'gols_visitante')
    list_filter = ('fase',) 
    search_fields = ('time_casa__nome', 'time_visitante__nome')

@admin.register(Palpite)
class PalpiteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'partida', 'palpite_casa', 'palpite_visitante', 'pontos')
    list_filter = ('usuario', 'partida__fase')

@admin.register(PalpitePodium)
class PalpitePodiumAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'campeao', 'vice', 'total_pontos')

@admin.register(PerguntaExtra)
class PerguntaExtraAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'pontos_valem', 'data_limite')

@admin.register(PalpiteExtra)
class PalpiteExtraAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'pergunta', 'resposta_usuario')