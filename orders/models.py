from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField('Имя', max_length=50)
    last_name = models.CharField('Фамилия', max_length=50)
    email = models.EmailField('Email')
    # добавил поле телефон
    phone = models.CharField('Телефон', max_length=20)
    address = models.CharField('Адрес', max_length=250)
    postal_code = models.CharField('Почтовый индекс', max_length=20)
    city = models.CharField('Город', max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField('Оплачен', default=False)
    
    class Meta:
        ordering = ('-created',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
    
    def __str__(self):
        return f'Заказ {self.id}'
    
    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product', related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField('Количество', default=1)
    
    def __str__(self):
        return str(self.id)
    
    def get_cost(self):
        return self.price * self.quantity
# Create your models here.
