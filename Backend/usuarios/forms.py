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


DIAS_SEMANA = (
    ('0', 'Lunes'),
    ('1', 'Martes'),
    ('2', 'Miércoles'),
    ('3', 'Jueves'),
    ('4', 'Viernes'),
    ('5', 'Sábado'),
    ('6', 'Domingo'),
)


class DisponibilidadProveedorForm(forms.Form):
    """Formulario semanal que permite guardar varios días en una sola operación."""

    dias = forms.MultipleChoiceField(
        choices=DIAS_SEMANA,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, horarios=None, **kwargs):
        super().__init__(*args, **kwargs)
        horarios = {str(h.dia_semana): h for h in (horarios or [])}
        initial_dias = []

        for valor, etiqueta in DIAS_SEMANA:
            horario = horarios.get(valor)
            if horario:
                initial_dias.append(valor)
            self.fields[f'hora_inicio_{valor}'] = forms.TimeField(
                required=False,
                input_formats=['%H:%M'],
                widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
                initial=horario.hora_inicio if horario else None,
                label=f'Inicio {etiqueta.lower()}',
            )
            self.fields[f'hora_fin_{valor}'] = forms.TimeField(
                required=False,
                input_formats=['%H:%M'],
                widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
                initial=horario.hora_fin if horario else None,
                label=f'Fin {etiqueta.lower()}',
            )

        if not self.is_bound:
            self.initial['dias'] = initial_dias

    def clean(self):
        cleaned_data = super().clean()
        dias = cleaned_data.get('dias', [])

        for dia, etiqueta in DIAS_SEMANA:
            if dia not in dias:
                continue

            inicio = cleaned_data.get(f'hora_inicio_{dia}')
            fin = cleaned_data.get(f'hora_fin_{dia}')
            if not inicio:
                self.add_error(f'hora_inicio_{dia}', 'Indica la hora inicial para este día.')
            if not fin:
                self.add_error(f'hora_fin_{dia}', 'Indica la hora final para este día.')
            if inicio and fin and inicio >= fin:
                self.add_error(f'hora_fin_{dia}', 'La hora inicial debe ser anterior a la hora final.')

        return cleaned_data


class PeriodoNoDisponibleForm(forms.Form):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        label='Fecha de inicio',
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        label='Fecha de fin',
        help_text='Déjala vacía si solo necesitas bloquear un día.',
    )
    motivo = forms.CharField(max_length=255, required=False, label='Motivo (opcional)')

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get('fecha_inicio')
        fin = cleaned_data.get('fecha_fin')

        if inicio and not fin:
            cleaned_data['fecha_fin'] = inicio
        elif inicio and fin and inicio > fin:
            self.add_error('fecha_fin', 'La fecha de inicio no puede ser posterior a la fecha de fin.')

        return cleaned_data
