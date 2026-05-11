from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Partida, Palpite, PerguntaExtra, PalpiteExtra

@receiver(post_save, sender=Partida)
def atualizar_pontos_ao_salvar_partida(sender, instance, **kwargs):
    """
    Sempre que uma partida for salva (editada no admin),
    este código roda automaticamente.
    """
    # Só calcula se o jogo já tiver placar preenchido
    if instance.gols_casa is not None and instance.gols_visitante is not None:
        print(f"Jogo {instance} atualizado! Recalculando palpites...")
        
        # Busca todos os palpites feitos para esse jogo
        palpites_dessa_partida = Palpite.objects.filter(partida=instance)
        
        for palpite in palpites_dessa_partida:
            palpite.calcular_pontuacao() # Chama aquela função do models.py
            print(f"Palpite de {palpite.usuario}: {palpite.pontos_ganhos} pontos.")


@receiver(post_save, sender=PerguntaExtra)
def atualizar_pontos_extras(sender, instance, **kwargs):
    """
    Quando o Admin define a resposta correta de uma pergunta extra,
    recalcula os pontos de todo mundo que respondeu.
    """
    if instance.resposta_correta:
        print(f"Pergunta '{instance.titulo}' respondida! Recalculando...")
        palpites = PalpiteExtra.objects.filter(pergunta=instance)
        for palpite in palpites:
            palpite.calcular_pontuacao()