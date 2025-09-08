# api/customer_serializers.py
from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "is_email_verified",
            "is_phone_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["is_email_verified", "is_phone_verified", "created_at", "updated_at"]
