from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from users.models import User


@admin.action(description="유저를 비활성화 시킵니다")
def deactivated_users(model_admin, request, users):
    for user in User.objects.all():
        user.is_active = False
        user.save()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    actions = (deactivated_users,)
    readonly_fields = ("last_login", "followers_list")
    list_display = [
        "is_active",
        "username",
        "age",
        "gender",
        "pk",
        "email",
        "is_admin",
        "login_type",
    ]
    list_filter = [
        "is_admin",
        "created_at",
        "updated_at",
        "is_active",
    ]
    fieldsets = [
        (
            "Profile",
            {
                "fields": (
                    "email",
                    "password",
                    "avatar",
                    "username",
                    "age",
                    "gender",
                    "followings",
                    "followers_list",
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_admin",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Important Dates",
            {
                "fields": ("last_login",),
                "classes": ("collapse",),
            },
        ),
    ]

    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "password1", "password2"],
            },
        ),
    ]
    search_fields = ["email", "username"]
    ordering = ["email"]
