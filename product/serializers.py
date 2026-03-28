from rest_framework import serializers
from .models import Product, Category, ProductReview


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    shop_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'keywords', 'description', 'price', 'stock', 'image',
                  'is_active', 'sales', 'created_at', 'category', 'category_name', 'shop_name']
        read_only_fields = ['sales', 'created_at']


class ProductReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ProductReview
        fields = ['id', 'rating', 'content', 'created_at', 'username']
        read_only_fields = ['id', 'created_at', 'username']
