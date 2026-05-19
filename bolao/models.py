from django.db import models
from django.contrib.auth.models import User

# 1. Tabela de Times
class Time(models.Model):
    GRUPO_CHOICES = [(chr(65+i), f'Grupo {chr(65+i)}') for i in range(12)] 
    
    nome = models.CharField(max_length=50)
    codigo = models.CharField(max_length=3) 
    grupo = models.CharField(max_length=1, choices=GRUPO_CHOICES)
    imagem = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.nome

# 2. Partida Inteligente
class Partida(models.Model):
    FASES = [
        ('GRUPOS', 'Fase de Grupos'),
        ('16AVOS', '16-avos de Final'),
        ('OITAVAS', 'Oitavas de Final'),
        ('QUARTAS', 'Quartas de Final'),
        ('SEMI', 'Semi-Final'),
        ('FINAL', 'Final'),
    ]

    numero_jogo = models.IntegerField(unique=True) 
    time_casa = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True, related_name='casa')
    time_visitante = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitante')
    gols_casa = models.IntegerField(null=True, blank=True)
    gols_visitante = models.IntegerField(null=True, blank=True)
    fase = models.CharField(max_length=20, choices=FASES)
    data_jogo = models.DateTimeField()
    referencia_casa = models.CharField(max_length=10, blank=True, null=True)
    referencia_visitante = models.CharField(max_length=10, blank=True, null=True)

    # CAMPO NOVO ADICIONADO PARA OS EMPATES #:
    vencedor_penaltis = models.ForeignKey(
        Time, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='vitorias_penaltis_reais',
        help_text="Apenas para o Admin: preencha quem venceu nos pênaltis caso o jogo real empate."
    )

    def __str__(self):
        nome_casa = self.time_casa.nome if self.time_casa else f"({self.referencia_casa})"
        nome_vis = self.time_visitante.nome if self.time_visitante else f"({self.referencia_visitante})"
        return f"Jogo {self.numero_jogo}: {nome_casa} x {nome_vis}"
    
    def save(self, *args, **kwargs):
        # 1. Primeiro, salva os resultados reais da Partida no banco
        super().save(*args, **kwargs)
        
        # 2. Puxa todos os palpites que os usuários fizeram PARA ESTE JOGO
        palpites = self.palpite_set.all() 
        for palpite in palpites:
            palpite.calcular_pontuacao() # Calcula a nota (ex: 10 pontos)
            palpite.save()               # O SEGREDO ESTÁ AQUI: Salva a nota no banco!
            print(f"Palpite de {palpite.usuario.username} atualizado para {palpite.pontos} pontos no banco de dados.")
        
        # 3. Chama o serviço de automação do mata-mata
        try:
            from .services import atualizar_confrontos, calcular_pontos_podium_geral
            atualizar_confrontos() # Monta chave do mata-mata
            calcular_pontos_podium_geral() # Calcula pontos de campeão
        except ImportError:
            pass

# 3. Palpites
class Palpite(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE)
    palpite_casa = models.IntegerField()
    palpite_visitante = models.IntegerField()
    pontos = models.IntegerField(default=0)

    # NOVO CAMPO: Guarda quem o usuário acha que passa de fase#
    vencedor_confronto = models.ForeignKey(
        'Time', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='palpites_vencidos'
    )

    class Meta:
        unique_together = ('usuario', 'partida')

    def __str__(self):
        return f"{self.usuario.username} - {self.partida}"
    
    # Automatiza o cálculo ao salvar
    def save(self, *args, **kwargs):
        self.calcular_pontuacao() # Calcula antes de salvar
        super().save(*args, **kwargs)

    def calcular_pontuacao(self):
        # Se o jogo ainda não tem resultado oficial, zera pontos e sai
        if self.partida.gols_casa is None:
            self.pontos = 0
            return
            
        real_casa = self.partida.gols_casa
        real_vis = self.partida.gols_visitante
        # CORREÇÃO 1: Usar os nomes corretos dos campos deste modelo
        palp_casa = self.palpite_casa
        palp_vis = self.palpite_visitante
        
        pontos = 0

        # Lógica de Vencedor
        res_real = 1 if real_casa > real_vis else (-1 if real_vis > real_casa else 0)
        res_palp = 1 if palp_casa > palp_vis else (-1 if palp_vis > palp_casa else 0)
        
        acertou_vencedor = (res_real == res_palp)
        acertou_placar_exato = (real_casa == palp_casa and real_vis == palp_vis)
        acertou_gols_casa = (real_casa == palp_casa)
        acertou_gols_vis = (real_vis == palp_vis)
        acertou_um_score = (acertou_gols_casa or acertou_gols_vis)

        # Regras de Pontuação
        if acertou_placar_exato:
            pontos = 30
        elif acertou_vencedor and acertou_um_score:
            pontos = 15
        elif acertou_vencedor:
            pontos = 10
        elif acertou_um_score:
            pontos = 5
            
        # CORREÇÃO 2: Salvar na variável correta 'self.pontos'
        self.pontos = pontos


# 4. Tabela "Invisível" para guardar o Pódio do Usuário
class PalpitePodium(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # O sistema preenche isso sozinho baseado nos palpites do mata-mata
    campeao = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True, related_name='aposta_campeao')
    vice = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True, related_name='aposta_vice')
    terceiro = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True, related_name='aposta_terceiro')
    quarto = models.ForeignKey(Time, on_delete=models.SET_NULL, null=True, blank=True, related_name='aposta_quarto')

    # Pontos ganhos (calculados no final da copa)
    pontos_campeao = models.IntegerField(default=0) # 500 pts
    pontos_vice = models.IntegerField(default=0)    # 450 pts
    pontos_terceiro = models.IntegerField(default=0)# 400 pts
    pontos_quarto = models.IntegerField(default=0)  # 350 pts

    def total_pontos(self):
        return self.pontos_campeao + self.pontos_vice + self.pontos_terceiro + self.pontos_quarto

    def __str__(self):
        return f"Pódio de {self.usuario.username}: 1. {self.campeao} | 2. {self.vice}"
    

# 5. Tabelas para Perguntas Extras Manuais (Opcional, mas sua view usa)
class PerguntaExtra(models.Model):
    titulo = models.CharField(max_length=200)
    pontos_valem = models.IntegerField()
    resposta_correta = models.CharField(max_length=100, blank=True, null=True)
    data_limite = models.DateTimeField()

    def __str__(self):
        return self.titulo

class PalpiteExtra(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    pergunta = models.ForeignKey(PerguntaExtra, on_delete=models.CASCADE)
    resposta_usuario = models.CharField(max_length=100)
    pontos_ganhos = models.IntegerField(default=0)

    class Meta:
        unique_together = ('usuario', 'pergunta')

    def __str__(self):
        return f"{self.usuario} - {self.pergunta}"