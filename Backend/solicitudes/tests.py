from datetime import date, datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Servicio
from usuarios.models import DisponibilidadProveedor, PerfilProveedor, PerfilUsuario
from .models import SolicitudReserva


class ReservaMismoDiaTests(APITestCase):
    def setUp(self):
        usuario_proveedor = get_user_model().objects.create_user(
            username='proveedor-horario@example.com', email='proveedor-horario@example.com', password='x'
        )
        perfil_proveedor = PerfilUsuario.objects.create(
            usuario=usuario_proveedor, rol=PerfilUsuario.Rol.PROVEEDOR
        )
        self.proveedor = PerfilProveedor.objects.create(
            perfil_usuario=perfil_proveedor, descripcion_profesional='Proveedor de pruebas'
        )
        self.cliente = get_user_model().objects.create_user(
            username='cliente-horario@example.com', email='cliente-horario@example.com', password='x'
        )
        PerfilUsuario.objects.create(usuario=self.cliente, rol=PerfilUsuario.Rol.CLIENTE)
        categoria = Categoria.objects.create(nombre='Servicios de prueba')
        self.servicio = Servicio.objects.create(
            proveedor=self.proveedor,
            categoria=categoria,
            nombre='Servicio de prueba',
            duracion_minutos=60,
            precio=25000,
        )
        DisponibilidadProveedor.objects.create(
            proveedor=self.proveedor,
            dia_semana=5,
            hora_inicio=time(8),
            hora_fin=time(17),
        )
        self.client.force_authenticate(self.cliente)

    def test_rechaza_horas_pasadas_y_la_hora_actual_del_dia(self):
        hoy = date(2026, 10, 31)
        ahora = datetime(2026, 10, 31, 12, 0, tzinfo=ZoneInfo('America/Bogota'))
        with patch('usuarios.disponibilidad.timezone.localdate', return_value=hoy), patch(
            'usuarios.disponibilidad.timezone.localtime', return_value=ahora
        ):
            for hora in ('11:00:00', '12:00:00'):
                respuesta = self.client.post('/api/solicitudes/', {
                    'servicio': self.servicio.pk,
                    'proveedor': self.proveedor.pk,
                    'fecha_solicitada': hoy.isoformat(),
                    'hora_solicitada': hora,
                    'direccion_atencion': 'Calle de prueba 123',
                    'barrio_sector': 'Centro',
                }, format='json')
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn('hora_solicitada', respuesta.data)

            futura = self.client.post('/api/solicitudes/', {
                'servicio': self.servicio.pk,
                'proveedor': self.proveedor.pk,
                'fecha_solicitada': hoy.isoformat(),
                'hora_solicitada': '13:00:00',
                'direccion_atencion': 'Calle de prueba 123',
                'barrio_sector': 'Centro',
            }, format='json')

        self.assertEqual(futura.status_code, 201, futura.data)
        self.assertEqual(futura.data['hora_solicitada'], '13:00:00')

        self.client.force_authenticate(self.proveedor.perfil_usuario.usuario)
        actualizacion = self.client.patch(f'/api/catalogo/servicios/{self.servicio.pk}/', {
            'nombre': 'Servicio actualizado',
            'precio': '40000.00',
            'duracion_minutos': 90,
        }, format='json')
        self.assertEqual(actualizacion.status_code, 200, actualizacion.data)

        solicitud = SolicitudReserva.objects.get(pk=futura.data['id'])
        self.assertEqual(solicitud.nombre_servicio_copia, 'Servicio de prueba')
        self.assertEqual(str(solicitud.precio_copia), '25000.00')
        self.assertEqual(solicitud.duracion_minutos_copia, 60)

        desactivacion = self.client.patch(f'/api/catalogo/servicios/{self.servicio.pk}/', {
            'estado': 'INACTIVO',
        }, format='json')
        self.assertEqual(desactivacion.status_code, 200, desactivacion.data)
        self.client.force_authenticate(self.cliente)
        solicitud_inactiva = self.client.post('/api/solicitudes/', {
            'servicio': self.servicio.pk,
            'proveedor': self.proveedor.pk,
            'fecha_solicitada': '2026-11-02',
            'hora_solicitada': '13:00:00',
            'direccion_atencion': 'Calle de prueba 123',
            'barrio_sector': 'Centro',
        }, format='json')
        self.assertEqual(solicitud_inactiva.status_code, 400)
        self.assertIn('servicio', solicitud_inactiva.data)
