from rest_framework import serializers
from .models import Merchant


class MerchantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Merchant
        fields = ['id', 'shop_name', 'description', 'logo', 'is_approved', 'created_at', 'username']
        read_only_fields = ['id', 'is_approved', 'created_at', 'username']
