from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Woofer", {"fields": ("auth_provider_id",)}),
    )
    list_display = UserAdmin.list_display + ("auth_provider_id",)
    search_fields = UserAdmin.search_fields + ("auth_provider_id",)

