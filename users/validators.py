import re
from rest_framework import status
from rest_framework.response import Response


def validate_password(password):
    """비밀번호 유효성 검사"""
    if len(password) < 8:
        return Response(
            {"error": "비밀번호는 8자리 이상이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST
        )
    if not re.search(r"[a-zA-Z]", password):
        return Response(
            {"error": "비밀번호는 하나 이상의 영문이 포함되어야 합니다."}, status=status.HTTP_400_BAD_REQUEST
        )
    if not re.search(r"\d", password):
        return Response(
            {"error": "비밀번호는 하나 이상의 숫자가 포함되어야 합니다."}, status=status.HTTP_400_BAD_REQUEST
        )
    if not re.search(r"[!@#$%^&*()]", password):
        return Response(
            {"error": "비밀번호는 적어도 하나 이상의 특수문자(!@#$%^&*())가 포함되어야 합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return password