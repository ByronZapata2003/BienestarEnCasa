from django.contrib import admin

from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'telefono', 'creado_en')
    list_filter = ('rol',)
    search_fields = ('usuario__username', 'usuario__email', 'telefono')
