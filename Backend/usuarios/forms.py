import socket
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        
        # 1. Validar si existe en la base de datos de la plataforma
        user_exists = User.objects.filter(email__iexact=email, is_active=True).exists()
        if not user_exists:
            raise forms.ValidationError("Este correo electrónico no está registrado en el sistema. Por favor ingresa uno existente.")

        # 2. Validar que el dominio del correo tenga un servidor de destino válido
        try:
            domain = email.split('@')[1]
            # Intenta resolver la dirección del dominio
            socket.gethostbyname(domain)
        except (IndexError, socket.gaierror):
            raise forms.ValidationError("El dominio del correo ingresado no es válido o no existe. Por favor verifica el correo ingresado.")

        return email