from django.contrib import admin

from .models import DisponibilidadProveedor, PerfilUsuario, PeriodoNoDisponible


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'telefono', 'creado_en')
    list_filter = ('rol',)
    search_fields = ('usuario__username', 'usuario__email', 'telefono')


@admin.register(DisponibilidadProveedor)
class DisponibilidadProveedorAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'dia_semana', 'hora_inicio', 'hora_fin')
    list_filter = ('dia_semana',)
    search_fields = ('proveedor__perfil_usuario__usuario__email', 'proveedor__perfil_usuario__usuario__first_name')


@admin.register(PeriodoNoDisponible)
class PeriodoNoDisponibleProveedorAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'fecha_inicio', 'fecha_fin', 'motivo')
    list_filter = ('fecha_inicio', 'fecha_fin')
    search_fields = ('proveedor__perfil_usuario__usuario__email', 'motivo')
