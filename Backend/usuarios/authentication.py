from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    # lee el access de la cookie httponly en vez del header Authorization
    def authenticate(self, request):
        access = request.COOKIES.get('access')
        if access is None:
            return None
        try:
            token = self.get_validated_token(access)
        except InvalidToken:
            return None  # token vencido: se trata como anonimo y las vistas protegidas responden 401 para que el front renueve
        # el navegador manda la cookie solo, asi que se exige el token CSRF igual que con sesiones
        SessionAuthentication().enforce_csrf(request)
        return self.get_user(token), token
