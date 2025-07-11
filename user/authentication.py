# user/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    """
    ① Authorization 헤더에 토큰이 있으면 그대로 사용
    ② 없으면 access 쿠키에서 꺼내서 인증
    """
    ACCESS_COOKIE = "access"      # views.py 에서 set_cookie 한 이름과 동일!

    def authenticate(self, request):
        header = self.get_header(request)

        # 1) 헤더 우선
        if header is not None:
            raw_token = self.get_raw_token(header)
        # 2) 헤더 없으면 쿠키
        else:
            raw_token = request.COOKIES.get(self.ACCESS_COOKIE)

        if raw_token is None:
            return None  # 인증 실패 → permission_classes 에 따라 401/403 처리

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
