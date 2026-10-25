from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from catalogo.models import Categoria, Servicio
from solicitudes.serializers import SolicitudReservaSerializer
from .models import (
    DisponibilidadProveedor,
    PerfilProveedor,
    PerfilUsuario,
    PeriodoNoDisponible,
)


class AutenticacionAPITest(APITestCase):
    datos_registro = {
        'nombres': 'Ana',
        'apellidos': 'Gomez',
        'email': 'ana@example.com',
        'password': 'ClaveSegura123!',
        'password_confirmacion': 'ClaveSegura123!',
        'rol': PerfilUsuario.Rol.CLIENTE,
        'telefono': '3001234567',
    }

    def test_registro_inicio_sesion_y_consulta_perfil(self):
        registro = self.client.post('/api/auth/registro/', self.datos_registro, format='json')
        self.assertEqual(registro.status_code, status.HTTP_201_CREATED)
        self.assertEqual(registro.data['rol'], PerfilUsuario.Rol.CLIENTE)

        inicio = self.client.post(
            '/api/auth/iniciar-sesion/',
            {'email': self.datos_registro['email'], 'password': self.datos_registro['password']},
            format='json',
        )
        self.assertEqual(inicio.status_code, status.HTTP_200_OK)
        # los tokens ya no viajan en el body (se revisa el JSON crudo que ve el navegador)
        self.assertNotIn(b'access', inicio.content)
        self.assertNotIn(b'refresh', inicio.content)
        self.assertTrue(inicio.cookies['access']['httponly'])
        self.assertTrue(inicio.cookies['refresh']['httponly'])

        perfil = self.client.get('/api/auth/mi-perfil/')  # el cliente de pruebas reenvia las cookies solo
        self.assertEqual(perfil.status_code, status.HTTP_200_OK)
        self.assertEqual(perfil.data['email'], self.datos_registro['email'])

        renovar = self.client.post('/api/auth/renovar-token/')
        self.assertEqual(renovar.status_code, status.HTTP_200_OK)
        self.assertIn('access', renovar.cookies)

        # con cookie de sesion, un PATCH sin token CSRF debe rechazarse
        sin_csrf = APIClient(enforce_csrf_checks=True)
        sin_csrf.cookies = self.client.cookies
        self.assertEqual(sin_csrf.patch('/api/auth/mi-perfil/', {}, format='json').status_code, status.HTTP_403_FORBIDDEN)

        salida = self.client.post('/api/auth/cerrar-sesion/')
        self.assertEqual(salida.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(salida.cookies['access'].value, '')
        self.assertEqual(self.client.get('/api/auth/mi-perfil/').status_code, status.HTTP_401_UNAUTHORIZED)


class HU11DisponibilidadProveedorAPITest(APITestCase):
    def crear_cuenta(self, email, rol):
        usuario = get_user_model().objects.create_user(
            username=email,
            email=email,
            password='ClaveSegura123!',
            first_name='Usuario',
        )
        perfil = PerfilUsuario.objects.create(usuario=usuario, rol=rol)
        return usuario, perfil

    def iniciar_sesion(self, email):
        respuesta = self.client.post(
            '/api/auth/iniciar-sesion/',
            {'email': email, 'password': 'ClaveSegura123!'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def setUp(self):
        self.proveedor, self.perfil_proveedor = self.crear_cuenta(
            'proveedor-hu11@example.com', PerfilUsuario.Rol.PROVEEDOR
        )
        self.proveedor_profesional = PerfilProveedor.objects.create(
            perfil_usuario=self.perfil_proveedor,
            descripcion_profesional='Servicios de bienestar',
        )
        self.cliente, self.perfil_cliente = self.crear_cuenta(
            'cliente-hu11@example.com', PerfilUsuario.Rol.CLIENTE
        )

    def test_disponibilidad_rechaza_rango_invalido_y_no_guarda(self):
        self.iniciar_sesion(self.proveedor.email)
        base = {'dia_semana': 0, 'hora_inicio': '10:00', 'hora_fin': '10:00'}

        respuesta = self.client.post('/api/proveedores/disponibilidad/', base, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(DisponibilidadProveedor.objects.filter(proveedor=self.proveedor_profesional).exists())

        base['hora_fin'] = '09:00'
        respuesta = self.client.post('/api/proveedores/disponibilidad/', base, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(DisponibilidadProveedor.objects.filter(proveedor=self.proveedor_profesional).exists())

    def test_proveedor_puede_configurar_consultar_y_actualizar_dias(self):
        self.iniciar_sesion(self.proveedor.email)
        lunes = self.client.post(
            '/api/proveedores/disponibilidad/',
            {'dia_semana': 0, 'hora_inicio': '08:00', 'hora_fin': '12:00'},
            format='json',
        )
        martes = self.client.post(
            '/api/proveedores/disponibilidad/',
            {'dia_semana': 1, 'hora_inicio': '09:00', 'hora_fin': '17:00'},
            format='json',
        )

        self.assertEqual(lunes.status_code, status.HTTP_201_CREATED)
        self.assertEqual(martes.status_code, status.HTTP_201_CREATED)
        consulta = self.client.get('/api/proveedores/disponibilidad/')
        self.assertEqual(consulta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(consulta.data), 2)

        actualizacion = self.client.patch(
            f"/api/proveedores/disponibilidad/{lunes.data['id']}/",
            {'hora_fin': '13:00'},
            format='json',
        )
        self.assertEqual(actualizacion.status_code, status.HTTP_200_OK)
        self.assertEqual(actualizacion.data['hora_fin'], '13:00:00')

    def test_periodo_no_disponible_admite_un_dia_y_rechaza_fechas_invertidas(self):
        self.iniciar_sesion(self.proveedor.email)
        fecha = (timezone.localdate() + timedelta(days=10)).isoformat()

        un_dia = self.client.post(
            '/api/proveedores/periodos-no-disponibles/',
            {'fecha_inicio': fecha, 'motivo': 'Día personal'},
            format='json',
        )
        self.assertEqual(un_dia.status_code, status.HTTP_201_CREATED)
        self.assertEqual(un_dia.data['fecha_fin'], fecha)

        actualizacion = self.client.patch(
            f"/api/proveedores/periodos-no-disponibles/{un_dia.data['id']}/",
            {'motivo': 'Cita médica'},
            format='json',
        )
        self.assertEqual(actualizacion.status_code, status.HTTP_200_OK)
        self.assertEqual(actualizacion.data['motivo'], 'Cita médica')

        invertido = self.client.post(
            '/api/proveedores/periodos-no-disponibles/',
            {'fecha_inicio': fecha, 'fecha_fin': (timezone.localdate() + timedelta(days=9)).isoformat()},
            format='json',
        )
        self.assertEqual(invertido.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PeriodoNoDisponible.objects.filter(proveedor=self.proveedor_profesional).count(), 1)

    def test_no_se_puede_consultar_disponibilidad_ajena_o_sin_rol_proveedor(self):
        _, otro_perfil = self.crear_cuenta(
            'otro-proveedor-hu11@example.com', PerfilUsuario.Rol.PROVEEDOR
        )
        otro_profesional = PerfilProveedor.objects.create(
            perfil_usuario=otro_perfil,
            descripcion_profesional='Otro proveedor',
        )
        otro_horario = DisponibilidadProveedor.objects.create(
            proveedor=otro_profesional,
            dia_semana=0,
            hora_inicio='08:00',
            hora_fin='12:00',
        )
        self.iniciar_sesion(self.proveedor.email)
        self.assertEqual(
            self.client.get(f'/api/proveedores/disponibilidad/{otro_horario.pk}/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        modificacion_ajena = self.client.patch(
            f'/api/proveedores/disponibilidad/{otro_horario.pk}/',
            {'hora_fin': '18:00'},
            format='json',
        )
        self.assertEqual(modificacion_ajena.status_code, status.HTTP_404_NOT_FOUND)
        otro_horario.refresh_from_db()
        self.assertEqual(str(otro_horario.hora_fin), '12:00:00')

        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/proveedores/disponibilidad/').status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            self.client.post(
                '/api/proveedores/disponibilidad/',
                {'dia_semana': 2, 'hora_inicio': '08:00', 'hora_fin': '12:00'},
                format='json',
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.iniciar_sesion(self.cliente.email)
        self.assertEqual(self.client.get('/api/proveedores/disponibilidad/').status_code, status.HTTP_403_FORBIDDEN)

    def test_periodo_y_horario_se_aplican_a_nuevas_reservas(self):
        categoria = Categoria.objects.create(nombre='Masajes HU11')
        servicio = Servicio.objects.create(
            proveedor=self.proveedor_profesional,
            categoria=categoria,
            nombre='Masaje de una hora',
            duracion_minutos=60,
            precio=50000,
        )
        fecha = timezone.localdate() + timedelta(days=10)
        dia = fecha.weekday()
        DisponibilidadProveedor.objects.create(
            proveedor=self.proveedor_profesional,
            dia_semana=dia,
            hora_inicio='10:00',
            hora_fin='12:00',
        )

        datos = {
            'proveedor': self.proveedor_profesional.pk,
            'servicio': servicio.pk,
            'fecha_solicitada': fecha.isoformat(),
            'hora_solicitada': '11:30',
            'direccion_atencion': 'Carrera 1 # 2-3',
            'barrio_sector': 'Centro',
        }
        datos['hora_solicitada'] = '10:30'
        serializer = SolicitudReservaSerializer(data=datos)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        datos['hora_solicitada'] = '11:30'
        serializer = SolicitudReservaSerializer(data=datos)
        self.assertFalse(serializer.is_valid())
        self.assertIn('hora_solicitada', serializer.errors)

        PeriodoNoDisponible.objects.create(
            proveedor=self.proveedor_profesional,
            fecha_inicio=fecha,
            fecha_fin=fecha,
        )
        datos['hora_solicitada'] = '10:00'
        serializer = SolicitudReservaSerializer(data=datos)
        self.assertFalse(serializer.is_valid())
        self.assertIn('fecha_solicitada', serializer.errors)

    def test_pagina_de_disponibilidad_renderiza_formularios_solo_para_proveedor(self):
        self.iniciar_sesion(self.proveedor.email)
        respuesta = self.client.get('/disponibilidad/')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertContains(respuesta, 'Guardar disponibilidad')
        self.assertContains(respuesta, 'Registrar periodo')

        self.client.cookies.clear()
        self.iniciar_sesion(self.cliente.email)
        self.assertEqual(self.client.get('/disponibilidad/').status_code, status.HTTP_403_FORBIDDEN)

    def test_formulario_django_guarda_horarios_y_rechaza_rangos_invalidos(self):
        self.iniciar_sesion(self.proveedor.email)
        datos = {
            'accion': 'guardar_disponibilidad',
            'dias': ['0', '1'],
            'hora_inicio_0': '08:00',
            'hora_fin_0': '12:00',
            'hora_inicio_1': '09:00',
            'hora_fin_1': '17:00',
        }

        guardado = self.client.post('/disponibilidad/', datos)
        self.assertEqual(guardado.status_code, status.HTTP_302_FOUND)
        self.assertEqual(DisponibilidadProveedor.objects.filter(proveedor=self.proveedor_profesional).count(), 2)

        datos['hora_fin_0'] = '08:00'
        rechazado = self.client.post('/disponibilidad/', datos)
        self.assertEqual(rechazado.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(DisponibilidadProveedor.objects.filter(proveedor=self.proveedor_profesional).count(), 2)
