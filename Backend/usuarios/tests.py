from rest_framework import status
from rest_framework.test import APITestCase

from .models import PerfilUsuario


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

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {inicio.data['access']}")
        perfil = self.client.get('/api/auth/mi-perfil/')
        self.assertEqual(perfil.status_code, status.HTTP_200_OK)
        self.assertEqual(perfil.data['email'], self.datos_registro['email'])
