from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from rest_framework.serializers import (
    ModelSerializer,
    SerializerMethodField,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
from .email_tokens import account_activation_token


class UserSerializer(ModelSerializer):
    is_host = SerializerMethodField()
    total_comments = SerializerMethodField()
    total_articles = SerializerMethodField()
    total_like_articles = SerializerMethodField()
    total_like_comments = SerializerMethodField()
    total_bookmark_articles = SerializerMethodField()
    total_followings = SerializerMethodField(read_only=True)
    total_followers = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        exclude = (
            "groups",
            "user_permissions",
        )
        extra_kwargs = {
            "followings": {
                "read_only": True,
            },
            "followers": {
                "read_only": True,
            },
            "password": {
                "write_only": True,
            },
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        html = render_to_string(
            "users/email_register.html",
            {
                "backend_base_url": settings.BACKEND_BASE_URL,
                "uidb64": urlsafe_base64_encode(force_bytes(user.id)).encode().decode(),
                "token": account_activation_token.make_token(user),
                "user": user,
            },
        )
        to_email = user.email
        send_mail(
            "안녕하세요 Cookai입니다. 인증메일이 도착했어요!",
            "_",
            settings.DEFAULT_FROM_MAIL,
            [to_email],
            html_message=html,
        )
        return user

    def get_is_host(self, user):
        request = self.context["request"]

        return request.user.id == user.id

    def get_total_comments(self, user):
        return user.comments.count()

    def get_total_articles(self, user):
        return user.article_set.count()

    def get_total_like_articles(self, user):
        return user.likes.count()

    def get_total_like_comments(self, user):
        return user.like_comments.count()

    def get_total_bookmark_articles(self, user):
        return user.bookmarks.count()

    def get_total_followings(self, user):
        return user.followings.count()

    def get_total_followers(self, user):
        return user.followers.count()


class PublicUserSerializer(ModelSerializer):
    is_host = SerializerMethodField()
    total_comments = SerializerMethodField()
    total_articles = SerializerMethodField()
    total_like_articles = SerializerMethodField()
    total_like_comments = SerializerMethodField()
    total_bookmark_articles = SerializerMethodField()
    total_followings = SerializerMethodField(read_only=True)
    total_followers = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        exclude = (
            "groups",
            "user_permissions",
            "password",
            "age",
            "gender",
        )
        extra_kwargs = {
            "followings": {
                "read_only": True,
            },
            "followers": {
                "read_only": True,
            },
        }

    def get_is_host(self, user):
        request = self.context["request"]

        return request.user.id == user.id

    def get_total_comments(self, user):
        return user.comments.count()

    def get_total_articles(self, user):
        return user.article_set.count()

    def get_total_like_articles(self, user):
        return user.likes.count()

    def get_total_like_comments(self, user):
        return user.like_comments.count()

    def get_total_bookmark_articles(self, user):
        return user.bookmarks.count()

    def get_total_followings(self, user):
        return user.followings.count()

    def get_total_followers(self, user):
        return user.followers.count()
    

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["id"] = user.id
        token["email"] = user.email
        token["username"] = user.username
        token["login_type"] = user.login_type
        token["avatar"] = user.avatar
        return token