from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import CookieJWTAuthentication
from .forms import DIAS_SEMANA, DisponibilidadProveedorForm, PeriodoNoDisponibleForm
from .models import DisponibilidadProveedor, PerfilProveedor, PeriodoNoDisponible
from .permissions import EsProveedorRegistrado
from .serializers import (
    DisponibilidadProveedorSerializer,
    PeriodoNoDisponibleProveedorSerializer,
)


class DisponibilidadProveedorListCreateView(generics.ListCreateAPIView):
    authentication_classes = (CookieJWTAuthentication,)
    permission_classes = (IsAuthenticated, EsProveedorRegistrado)
    serializer_class = DisponibilidadProveedorSerializer

    def get_queryset(self):
        return DisponibilidadProveedor.objects.filter(
            proveedor__perfil_usuario=self.request.user.perfil
        )

    def perform_create(self, serializer):
        serializer.save(proveedor=self.get_perfil_proveedor())

    def get_perfil_proveedor(self):
        proveedor, _ = PerfilProveedor.objects.get_or_create(
            perfil_usuario=self.request.user.perfil,
            defaults={'descripcion_profesional': ''},
        )
        return proveedor


class DisponibilidadProveedorDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = (CookieJWTAuthentication,)
    permission_classes = (IsAuthenticated, EsProveedorRegistrado)
    serializer_class = DisponibilidadProveedorSerializer

    def get_queryset(self):
        return DisponibilidadProveedor.objects.filter(
            proveedor__perfil_usuario=self.request.user.perfil
        )


class PeriodoNoDisponibleListCreateView(generics.ListCreateAPIView):
    authentication_classes = (CookieJWTAuthentication,)
    permission_classes = (IsAuthenticated, EsProveedorRegistrado)
    serializer_class = PeriodoNoDisponibleProveedorSerializer

    def get_queryset(self):
        return PeriodoNoDisponible.objects.filter(
            proveedor__perfil_usuario=self.request.user.perfil
        )

    def perform_create(self, serializer):
        proveedor, _ = PerfilProveedor.objects.get_or_create(
            perfil_usuario=self.request.user.perfil,
            defaults={'descripcion_profesional': ''},
        )
        serializer.save(proveedor=proveedor)


class PeriodoNoDisponibleDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = (CookieJWTAuthentication,)
    permission_classes = (IsAuthenticated, EsProveedorRegistrado)
    serializer_class = PeriodoNoDisponibleProveedorSerializer

    def get_queryset(self):
        return PeriodoNoDisponible.objects.filter(
            proveedor__perfil_usuario=self.request.user.perfil
        )


class GestionarDisponibilidadPageView(APIView):
    """Página HTML con formularios Django; no necesita JavaScript en el navegador."""

    authentication_classes = (CookieJWTAuthentication,)
    permission_classes = (IsAuthenticated, EsProveedorRegistrado)
    template_name = 'users/disponibilidad-proveedor.html'

    def obtener_horarios(self, user):
        return DisponibilidadProveedor.objects.filter(proveedor__perfil_usuario=user.perfil)

    def obtener_periodos(self, user):
        return PeriodoNoDisponible.objects.filter(proveedor__perfil_usuario=user.perfil)

    def obtener_perfil_proveedor(self, user):
        proveedor, _ = PerfilProveedor.objects.get_or_create(
            perfil_usuario=user.perfil,
            defaults={'descripcion_profesional': ''},
        )
        return proveedor

    def contexto(self, request, disponibilidad_form=None, periodo_form=None, periodo_editando=None):
        horarios = list(self.obtener_horarios(request.user))
        horarios_por_dia = {horario.dia_semana: horario for horario in horarios}
        disponibilidad_form = disponibilidad_form or DisponibilidadProveedorForm(horarios=horarios)
        dias_seleccionados = set(disponibilidad_form['dias'].value() or [])
        return {
            'disponibilidad_form': disponibilidad_form,
            'periodo_form': periodo_form or PeriodoNoDisponibleForm(),
            'periodo_editando': periodo_editando,
            'dias': [
                {
                    'valor': valor,
                    'etiqueta': etiqueta,
                    'horario': horarios_por_dia.get(valor),
                    'activo': str(valor) in dias_seleccionados,
                    'hora_inicio': disponibilidad_form[f'hora_inicio_{valor}'],
                    'hora_fin': disponibilidad_form[f'hora_fin_{valor}'],
                }
                for valor, etiqueta in DisponibilidadProveedor.DIAS_SEMANA
            ],
            'periodos': self.obtener_periodos(request.user),
        }

    def get(self, request):
        periodo_editando = None
        periodo_form = None
        periodo_id = request.query_params.get('editar_periodo')
        if periodo_id:
            periodo_editando = get_object_or_404(
                PeriodoNoDisponible,
                pk=periodo_id,
                proveedor__perfil_usuario=request.user.perfil,
            )
            periodo_form = PeriodoNoDisponibleForm(initial={
                'fecha_inicio': periodo_editando.fecha_inicio,
                'fecha_fin': periodo_editando.fecha_fin,
                'motivo': periodo_editando.motivo,
            })
        return render(
            request._request,
            self.template_name,
            self.contexto(request, periodo_form=periodo_form, periodo_editando=periodo_editando),
        )

    def post(self, request):
        form_data = request._request.POST
        accion = form_data.get('accion')

        if accion == 'guardar_disponibilidad':
            form = DisponibilidadProveedorForm(form_data, horarios=self.obtener_horarios(request.user))
            if form.is_valid():
                proveedor = self.obtener_perfil_proveedor(request.user)
                seleccionados = set(form.cleaned_data['dias'])
                with transaction.atomic():
                    for dia, _ in DIAS_SEMANA:
                        if dia in seleccionados:
                            DisponibilidadProveedor.objects.update_or_create(
                                proveedor=proveedor,
                                dia_semana=int(dia),
                                defaults={
                                    'hora_inicio': form.cleaned_data[f'hora_inicio_{dia}'],
                                    'hora_fin': form.cleaned_data[f'hora_fin_{dia}'],
                                },
                            )
                        else:
                            DisponibilidadProveedor.objects.filter(
                                proveedor=proveedor,
                                dia_semana=int(dia),
                            ).delete()
                messages.success(request._request, 'La disponibilidad fue guardada correctamente.')
                return redirect('pagina-disponibilidad')

            return render(
                request._request,
                self.template_name,
                self.contexto(request, disponibilidad_form=form),
                status=400,
            )

        if accion == 'crear_periodo':
            form = PeriodoNoDisponibleForm(form_data)
            if form.is_valid():
                proveedor = self.obtener_perfil_proveedor(request.user)
                PeriodoNoDisponible.objects.create(
                    proveedor=proveedor,
                    **form.cleaned_data,
                )
                messages.success(request._request, 'El periodo no disponible fue registrado correctamente.')
                return redirect('pagina-disponibilidad')

            return render(
                request._request,
                self.template_name,
                self.contexto(request, periodo_form=form),
                status=400,
            )

        if accion == 'actualizar_periodo':
            periodo = get_object_or_404(
                PeriodoNoDisponible,
                pk=form_data.get('periodo_id'),
                proveedor__perfil_usuario=request.user.perfil,
            )
            form = PeriodoNoDisponibleForm(form_data)
            if form.is_valid():
                for campo, valor in form.cleaned_data.items():
                    setattr(periodo, campo, valor)
                periodo.save(update_fields=('fecha_inicio', 'fecha_fin', 'motivo'))
                messages.success(request._request, 'El periodo no disponible fue actualizado correctamente.')
                return redirect('pagina-disponibilidad')

            return render(
                request._request,
                self.template_name,
                self.contexto(request, periodo_form=form, periodo_editando=periodo),
                status=400,
            )

        if accion == 'eliminar_periodo':
            proveedor = self.obtener_perfil_proveedor(request.user)
            periodo = get_object_or_404(
                PeriodoNoDisponible,
                pk=form_data.get('periodo_id'),
                proveedor=proveedor,
            )
            periodo.delete()
            messages.success(request._request, 'El periodo no disponible fue eliminado.')
            return redirect('pagina-disponibilidad')

        messages.error(request._request, 'La operación solicitada no es válida.')
        return redirect('pagina-disponibilidad')


class DisponibilidadPublicaView(APIView):
    """Horario que el cliente puede consultar para armar la solicitud. Solo lectura."""
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request, pk):
        proveedor = get_object_or_404(PerfilProveedor, pk=pk)
        dias = [
            {
                'dia_semana': d.dia_semana,
                'hora_inicio': d.hora_inicio.strftime('%H:%M'),
                'hora_fin': d.hora_fin.strftime('%H:%M'),
            }
            for d in proveedor.disponibilidades.all().order_by('dia_semana', 'hora_inicio')
        ]
        periodos = [
            {
                'fecha_inicio': p.fecha_inicio.isoformat(),
                'fecha_fin': p.fecha_fin.isoformat(),
            }
            for p in proveedor.periodos_no_disponibles.all().order_by('fecha_inicio')
        ]
        return Response({'configurado': bool(dias), 'dias': dias, 'periodos': periodos})
