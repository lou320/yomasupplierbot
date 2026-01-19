from django.contrib import admin
from .models import Product, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model.
    """
    list_display = ('name', 'telegram_username', 'phone', 'address', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'telegram_username', 'phone', 'telegram_id')
    readonly_fields = ('telegram_id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Telegram Info', {
            'fields': ('telegram_id', 'telegram_username', 'first_name')
        }),
        ('Contact Information', {
            'fields': ('name', 'phone', 'address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Product model.
    """
    list_display = ('name', 'price', 'status', 'stock_count', 'expiry_date', 'created_at')
    list_filter = ('status', 'expiry_date', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock_count', 'status')
        }),
        ('Dates', {
            'fields': ('expiry_date', 'created_at')
        }),
    )
