from rest_framework import status
from rest_framework.test import APIClient, APITestCase

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
