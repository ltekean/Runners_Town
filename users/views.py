import re
import requests
from django.db import transaction
from django.db.models import Count
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import redirect
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ParseError,
)
from rest_framework.generics import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    PublicUserSerializer,
)
from users import serializers
from users.models import User
from users.validators import validate_password
from users.email_tokens import account_activation_token
# Create your views here.
class UserView(APIView):
    # """유저전체보기, 주석 추가 예정"""

    def get(self, request):
        user = User.objects.all()
        serializer = UserSerializer(user, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        password2 = request.data.get("second_password")
        username = request.data.get("username")
        if not password or not password2:
            return Response(
                {"error": "비밀번호 입력은 필수입니다!"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not email:
            return Response(
                {"error": "이메일 입력은 필수입니다!"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not username:
            return Response(
                {"error": "닉네임 입력은 필수입니다!"}, status=status.HTTP_400_BAD_REQUEST
            )
        if password != password2:
            return Response(
                {"error": "비밀번호가 일치하지 않습니다!"}, status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "해당 이메일을 가진 유저가 이미 있습니다!"}, status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "해당 닉네임을 가진 유저가 이미 있습니다!"}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(password) < 8:
            return Response(
                {"error": "비밀번호는 8자리 이상이어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[a-zA-Z]", password):
            return Response(
                {"error": "비밀번호는 하나 이상의 영문이 포함되어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"\d", password):
            return Response(
                {"error": "비밀번호는 하나 이상의 숫자가 포함되어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[!@#$%^&*()]", password):
            return Response(
                {"error": "비밀번호는 적어도 하나 이상의 특수문자(!@#$%^&*())가 포함되어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UserSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        

class UserAvatarGetUploadURLView(APIView):
    def post(self, request):
        """GetUploadURL.post

        사용자가 사진을 첨부해서 클라우드플레어에 전송하기전에 먼저 일회용 업로드 url을 요청합니다.

        Args:
            url (str): 클라우드플레어에서 미리 지정한 일회용 url 요청 링크
            one_time_url (str): post요청이 성공할 경우 클라우드플레어에서 온 response. 일회용 업로드 url을 포함하고 있습니다.
        return:
            result(str)): 일회용 url

        """
        url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CF_ID}/images/v2/direct_upload"
        one_time_url = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.CF_TOKEN}",
            },
        )
        one_time_url = one_time_url.json()
        result = one_time_url.get("result")
        return Response(result)
    

class UserSignUpPermitView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            if account_activation_token.check_token(user, token):
                User.objects.filter(pk=uid).update(is_active=True)

                html = render_to_string(
                    "users/email_welcome.html",
                    {
                        "front_base_url": settings.FRONT_BASE_URL,
                        "user": user,
                    },
                )
                to_email = user.email
                send_mail(
                    "안녕하세요 Cookai입니다. 회원가입을 축하드립니다!",
                    "_",
                    settings.DEFAULT_FROM_MAIL,
                    [to_email],
                    html_message=html,
                )
                return redirect(f"{settings.FRONT_BASE_URL}/login.html")
            return Response({"error": "AUTH_FAIL"}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({"error": "KEY_ERROR"}, status=status.HTTP_400_BAD_REQUEST)


class UserResetPasswordPermitView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            if account_activation_token.check_token(user, token):
                return redirect(
                    f"{settings.FRONT_BASE_URL}/users/password_change.html?uid={uid}&uidb64={uidb64}&token={token}"
                )
            return Response({"error": "AUTH_FAIL"}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return Response({"error": "KEY_ERROR"}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class KakaoLoginView(APIView):
    def get(self, request):
        return Response(settings.KK_API_KEY, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            # with transaction.atomic():
            auth_code = request.data.get("code")
            kakao_token_api = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": settings.KK_API_KEY,
                "redirect_uri": f"{settings.FRONT_BASE_URL}/index.html",
                "code": auth_code,
            }
            kakao_token = requests.post(
                kakao_token_api,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
            )
            access_token = kakao_token.json().get("access_token")
            user_data = requests.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
                },
            )
            user_data = user_data.json()
            data = {
                "avatar": user_data.get("properties").get("profile_image"),
                "email": user_data.get("kakao_account").get("email"),
                "username": user_data.get("properties").get("nickname"),
                "gender": user_data.get("kakao_account").get("gender"),
                "login_type": "kakao",
                "is_active": True,
            }
            return social_login_validate(**data)
        except Exception:
            return Response({"error": "로그인 실패!"}, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    def get(self, request):
        return Response(settings.GC_ID, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            # with transaction.atomic():
            access_token = request.data["access_token"]
            user_data = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_data = user_data.json()
            data = {
                "email": user_data.get("email"),
                "username": user_data.get("name"),
                "avatar": user_data.get("picture"),
                "login_type": "google",
                "is_active": True,
            }
            return social_login_validate(**data)
        except Exception:
            return Response({"error": "로그인 실패!"}, status=status.HTTP_400_BAD_REQUEST)


class NaverLoginView(APIView):
    def get(self, request):
        return Response(settings.NC_ID, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            # with transaction.atomic():
            code = request.data.get("naver_code")
            state = request.data.get("state")
            access_token = requests.post(
                f"https://nid.naver.com/oauth2.0/token?grant_type=authorization_code&code={code}&client_id={settings.NC_ID}&client_secret={settings.NC_SECRET}&state={state}",
                headers={"Accept": "application/json"},
            )
            access_token = access_token.json().get("access_token")
            user_data = requests.get(
                "https://openapi.naver.com/v1/nid/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            user_data = user_data.json().get("response")
            data = {
                "avatar": user_data.get("profile_image"),
                "email": user_data.get("email"),
                "username": user_data.get("nickname"),
                "login_type": "naver",
                "is_active": True,
            }
            return social_login_validate(**data)
        except Exception:
            return Response({"error": "로그인 실패!"}, status=status.HTTP_400_BAD_REQUEST)


def social_login_validate(**kwargs):
    # """소셜 로그인, 회원가입"""
    data = {k: v for k, v in kwargs.items()}
    email = data.get("email")
    login_type = data.get("login_type")
    if not email:
        return Response(
            {"error": "해당 계정에 email정보가 없습니다."}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        user = User.objects.get(email=email)
        if user.is_active == False:
            return Response(
                {"error": "해당 유저는 휴면계정입니다!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if login_type == user.login_type:
            refresh = RefreshToken.for_user(user)
            access_token = serializers.CustomTokenObtainPairSerializer.get_token(user)
            return Response(
                {"refresh": str(refresh), "access": str(access_token.access_token)},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "같은 이메일로 이미 가입된 계정이 있습니다!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except User.DoesNotExist:
        # with transaction.atomic():
        new_user = User.objects.create(**data)
        new_user.set_unusable_password()
        new_user.save()
        refresh = RefreshToken.for_user(new_user)
        access_token = serializers.CustomTokenObtainPairSerializer.get_token(new_user)
        html = render_to_string(
            "users/email_welcome.html",
            {
                "front_base_url": settings.FRONT_BASE_URL,
                "user": new_user,
            },
        )
        to_email = new_user.email
        send_mail(
            "안녕하세요 Cookai입니다. 회원가입을 축하드립니다!",
            "_",
            settings.DEFAULT_FROM_MAIL,
            [to_email],
            html_message=html,
        )
        return Response(
            {"refresh": str(refresh), "access": str(access_token.access_token)},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    # """비밀번호 찾기. 이메일 인증하면 비밀번호 재설정할 기회를 준다. 주석추가에정,이메일 인증 추가예정"""

    def post(self, request):
        try:
            user_email = request.data.get("email")
            user = User.objects.get(email=user_email)
            if user:
                if user.login_type == "normal" or user.is_active == False:
                    html = render_to_string(
                        "users/email_password_reset.html",
                        {
                            "backend_base_url": settings.BACKEND_BASE_URL,
                            "uidb64": urlsafe_base64_encode(force_bytes(user.id))
                            .encode()
                            .decode(),
                            "token": account_activation_token.make_token(user),
                            "user": user,
                        },
                    )
                    to_email = user.email
                    send_mail(
                        "안녕하세요 Cookai입니다. 비밀번호 초기화 메일이 도착했어요!",
                        "_",
                        settings.DEFAULT_FROM_MAIL,
                        [to_email],
                        html_message=html,
                    )
                    return Response(
                        {"message": "이메일 전송 완료!"}, status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {"error": "해당 이메일은 소셜로그인 이메일입니다!"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except User.DoesNotExist:
            return Response(
                {"error": "해당 이메일에 일치하는 사용자가 없습니다!"}, status=status.HTTP_400_BAD_REQUEST
            )

    def put(self, request):
        uidb64 = request.data.get("uidb64")
        token = request.data.get("token")
        user_id = request.data.get("user_id")
        new_first_password = request.data.get("new_first_password")
        new_second_password = request.data.get("new_second_password")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "일치하는 유저가 존재하지 않습니다!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not uidb64 or not token:
            return Response({"error": "잘못된 접근입니다!"}, status=status.HTTP_403_FORBIDDEN)
        if not new_first_password or not new_second_password:
            return Response(
                {"error": "비밀번호 입력은 필수입니다!"}, status=status.HTTP_400_BAD_REQUEST
            )
        if new_first_password != new_second_password:
            return Response(
                {"error": "비밀번호가 일치하지 않습니다!"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_second_password) < 8:
            return Response(
                {"error": "비밀번호는 8자리 이상이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not re.search(r"[a-zA-Z]", new_second_password):
            return Response(
                {"error": "비밀번호는 하나 이상의 영문이 포함되어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"\d", new_second_password):
            return Response(
                {"error": "비밀번호는 하나 이상의 숫자가 포함되어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[!@#$%^&*()]", new_second_password):
            return Response(
                {"error": "비밀번호는 적어도 하나 이상의 특수문자(!@#$%^&*())가 포함되어야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account_activation_token.check_token(user, token):
            try:
                user.set_password(new_second_password)
                user.is_active = True
                user.save()
                return Response(
                    {"message": "비밀번호가 재설정 되었습니다!"}, status=status.HTTP_200_OK
                )
            except Exception:
                raise ParseError
        else:
            return Response({"error": "잘못된 접근입니다!"}, status=status.HTTP_403_FORBIDDEN)

    def patch(self, request):
        uidb64 = request.data.get("uidb64")
        token = request.data.get("token")
        user_id = request.data.get("user_id")
        user = get_object_or_404(User, id=user_id)
        if not uidb64 or not token:
            return Response({"error": "잘못된 접근입니다!"}, status=status.HTTP_403_FORBIDDEN)
        if user.login_type != "normal":
            user.is_active = True
            user.save()
            return Response({"message": "복구되었습니다!"}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "해당 회원은 소셜 계정이 아닙니다!"}, status=status.HTTP_403_FORBIDDEN
            )


class ChangePasswordView(APIView):
    # """노말 로그인 회원만 비번 바꾸기. 주석추가예정"""

    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        if user.login_type == "normal":
            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")
            new_password2 = request.data.get("new_password2")
            if not old_password or not new_password or not new_password2:
                return Response(
                    {"error": "비밀번호입력은 필수입니다!"}, status=status.HTTP_400_BAD_REQUEST
                )
            if old_password == new_password:
                return Response(
                    {"error": "예전 비밀번호와 새 비밀번호가 일치합니다!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if new_password != new_password2:
                return Response(
                    {"error": "비밀번호가 일치하지 않습니다!"}, status=status.HTTP_400_BAD_REQUEST
                )
            if len(new_password) < 8:
                return Response(
                    {"error": "비밀번호는 8자리 이상이어야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not re.search(r"[a-zA-Z]", new_password):
                return Response(
                    {"error": "비밀번호는 하나 이상의 영문이 포함되어야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not re.search(r"\d", new_password):
                return Response(
                    {"error": "비밀번호는 하나 이상의 숫자가 포함되어야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not re.search(r"[!@#$%^&*()]", new_password):
                return Response(
                    {"error": "비밀번호는 적어도 하나 이상의 특수문자(!@#$%^&*())가 포함되어야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                return Response(
                    {"message": "비밀번호가 변경되었습니다!"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "현재 비밀번호가 일치하지 않습니다!"}, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"error": "비밀번호 변경은 일반 로그인 계정만 가능합니다!"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, user_id):
        # """유저 프로필 조회 주석 추가 예정"""

        user = get_object_or_404(User, id=user_id)
        if request.user.id == user_id:
            serializer = UserSerializer(
                user,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            serializer = PublicUserSerializer(
                user,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, user_id):
        # """유저 프로필 수정"""
        user = get_object_or_404(User, id=user_id)
        if request.user.id == user_id:
            serializer = UserSerializer(
                user,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            raise PermissionDenied

    def patch(self, request, user_id):
        """유저 삭제, 주석 추가 예정"""
        user = get_object_or_404(User, id=user_id)
        if user.login_type == "normal":
            if request.user.id == user_id and user.check_password(
                request.data.get("password")
            ):
                user = request.user
                user.is_active = False
                user.save()
                return Response({"message": "삭제되었습니다!"}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "비밀번호가 일치하지 않습니다!"}, status=status.HTTP_403_FORBIDDEN
                )
        else:
            if request.user.id == user_id:
                user = request.user
                user.is_active = False
                user.save()
                return Response({"message": "삭제되었습니다!"}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "권한이 없습니다!"}, status=status.HTTP_403_FORBIDDEN
                )


# class UserDetailArticlesView(generics.ListAPIView):
#     pagination_class = ArticlePagination
#     serializer_class = ArticleListSerializer
#     queryset = Article.objects.none()

#     def my_article(self):
#         return Article.objects.filter(author_id=self.user_id)

#     def liked_article(self):
#         return Article.objects.filter(like=self.user_id)

#     def bookmarked_article(self):
#         return Article.objects.filter(bookmark=self.user_id)

#     def follow_article(self):
#         return Article.objects.filter(author__followers=self.user_id)

#     def get_queryset(self):
#         query_types = {
#             "0": self.my_article,
#             "1": self.liked_article,
#             "2": self.bookmarked_article,
#             "3": self.follow_article,
#         }
#         query_key = self.request.GET.get("filter", None)
#         order = self.request.GET.get("order", None)
#         queryset = query_types.get(query_key, self.my_article)()
#         if order == "1":
#             queryset = queryset.annotate(like_count=Count("like")).order_by(
#                 "-like_count"
#             )
#         else:
#             queryset = queryset.order_by("-created_at")
#         return queryset

#     def get(self, request, *args, **kwargs):
#         self.user_id = kwargs.get("user_id", None)
#         return super().get(request, *args, **kwargs)