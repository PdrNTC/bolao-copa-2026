from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')), # <--- Adicione esta linha (Login/Logout nativos)
    path('', include('bolao.urls')), # <--- Adicione isso. Tudo do app 'bolao' vai pra raiz.
]
