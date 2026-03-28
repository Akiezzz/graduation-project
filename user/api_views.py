from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import login, logout, authenticate
from .models import User
from .serializers import UserSerializer, RegisterSerializer


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_register(request):
    s = RegisterSerializer(data=request.data)
    if s.is_valid():
        user = s.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_login(request):
    user = authenticate(username=request.data.get('username'), password=request.data.get('password'))
    if user:
        login(request, user)
        return Response(UserSerializer(user).data)
    return Response({'error': '用户名或密码错误'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def api_logout(request):
    logout(request)
    return Response({'message': '已退出'})


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
