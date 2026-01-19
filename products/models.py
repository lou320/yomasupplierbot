from django.db import models


class UserProfile(models.Model):
    """
    User profile model for storing customer information.
    """
    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    telegram_username = models.CharField(max_length=255, blank=True, verbose_name='Username')
    first_name = models.CharField(max_length=255, blank=True, verbose_name='First Name')
    name = models.CharField(max_length=255, verbose_name='Name')
    phone = models.CharField(max_length=50, verbose_name='Phone Number')
    address = models.TextField(verbose_name='Address')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} (@{self.telegram_username or self.telegram_id})"


class Product(models.Model):
    """
    Product model for managing inventory items.
    """
    
    # Status choices
    IN_STOCK = 'IN_STOCK'
    ON_THE_WAY = 'ON_THE_WAY'
    
    STATUS_CHOICES = [
        (IN_STOCK, 'In Stock'),
        (ON_THE_WAY, 'On The Way'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Product Name')
    description = models.TextField(blank=True, verbose_name='Description')
    image = models.ImageField(upload_to='products/', verbose_name='Product Image')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Price')
    stock_count = models.IntegerField(default=0, verbose_name='Stock Count')
    expiry_date = models.DateField(verbose_name='Expiry Date')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=IN_STOCK,
        verbose_name='Status'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
