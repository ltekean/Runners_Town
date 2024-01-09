from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from .validators import validate_password

# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None):
        if not email:
            raise ValueError("User must have an email")
        if not password:
            raise ValueError("User must have a password")
        user = self.model(
            email=self.normalize_email(email),
            username=username,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None):
        try:
            user = User.objects.get(username=username)
            raise ValueError("해당 닉네임이 이미 존재합니다!")
        except User.DoesNotExist:
            pass
        user = self.create_user(
            email,
            username=username,
            password=password,
        )
        user.is_active = True
        user.is_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


"""유저 모델

    AbstractUser 유저 모델을 커스텀한 유저 모델입니다.

    Attributes:
        LoginTypeChoices(class) : 회원가입 유형(일반,카카오,구글,네이버)
        GenderTypeChoices(class) : 성별 유형(male,female)
        email (str): 이메일, 필수
        username (str) : 닉네임, 필수
        password (str): 패스워드, 필수
        avatar(str) : 유저의 프로필 사진을 url로 가져옵니다.
        age(date) : 나이
        gender(str) : 성별
        updated_at (date): 수정시간
        created_at (date): 가입시간
        login_type (str): 회원가입 유형의 종류를 지정
        is_active (bool): 활성 여부
        is_admin (bool): 관리자 여부
        is_host(bool): 본인 여부
        followings(ManyToMany) : 팔로잉 목록
    """


class User(AbstractUser):
    class LoginTypeChoices(models.TextChoices):
        NORMAL = ("normal", "일반")
        KAKAO = ("kakao", "카카오")
        GOOGLE = ("google", "구글")
        NAVER = ("naver", "네이버")

    class GenderTypeChoices(models.TextChoices):
        MALE = ("male", "Male")
        FEMALE = ("female", "Female")

    email = models.EmailField(
        max_length=255,
        unique=True,
    )
    username = models.CharField(
        max_length=23,
        unique=True,
    )
    password = models.CharField(max_length=256, validators=[validate_password])
    avatar = models.URLField(
        blank=True,
        null=True,
    )
    age = models.DateField(
        blank=True,
        null=True,
    )
    gender = models.CharField(
        choices=GenderTypeChoices.choices,
        max_length=10,
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    login_type = models.CharField(
        max_length=15,
        choices=LoginTypeChoices.choices,
        default="normal",
    )
    is_active = models.BooleanField(
        default=False,
    )
    is_admin = models.BooleanField(
        default=False,
    )
    is_host = models.BooleanField(
        default=False,
    )
    followings = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="followers",
        blank=True,
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
    objects = UserManager()

    def followers_list(self):
        follower_list = ""
        followers = self.followers.all()
        for follower in followers:
            follower_list += f"{follower.username}\n"
        return follower_list

    def __str__(self):
        return str(self.username)

    class Meta:
        verbose_name_plural = "Users"