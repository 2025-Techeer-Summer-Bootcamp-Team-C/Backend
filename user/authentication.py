# user/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    ACCESS_COOKIE = "access"      # views.py 에서 set_cookie 한 이름과 동일!

    def authenticate(self, request):
        header = self.get_header(request)

        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = request.COOKIES.get(self.ACCESS_COOKIE)

        if raw_token is None:
            return None  

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
