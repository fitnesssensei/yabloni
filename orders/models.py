from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError

class OrderStatus(models.TextChoices):
    NEW = 'new', 'Новый'
    PROCESSING = 'processing', 'В обработке'
    SHIPPED = 'shipped', 'Отправлен'
    DELIVERED = 'delivered', 'Доставлен'
    CANCELLED = 'cancelled', 'Отменен'

# Валидатор для российских телефонных номеров
phone_validator = RegexValidator(
    regex=r'^(\+7|8)?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$',
    message='Введите корректный российский телефонный номер в формате: +7 (XXX) XXX-XX-XX или 8XXXXXXXXXX'
)

def validate_phone(value):
    """Дополнительная валидация телефонного номера"""
    # Удаляем все символы кроме цифр
    phone_digits = ''.join(filter(str.isdigit, value))
    
    # Проверяем количество цифр
    if len(phone_digits) != 11:
        raise ValidationError('Телефонный номер должен содержать 11 цифр')
    
    # Проверяем, что номер начинается с 7 или 8
    if not phone_digits.startswith(('7', '8')):
        raise ValidationError('Телефонный номер должен начинаться с 7 или 8')

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    last_name = models.CharField('Фамилия', max_length=50)
    first_name = models.CharField('Имя', max_length=50)
    patronymic = models.CharField('Отчество', max_length=50, blank=True)
    email = models.EmailField('Email')
    phone = models.CharField(
        'Телефон', 
        max_length=20,
        validators=[phone_validator, validate_phone],
        help_text='Формат: +7 (XXX) XXX-XX-XX или 8XXXXXXXXXX'
    )
    address = models.CharField('Адрес', max_length=250)
    postal_code = models.CharField('Почтовый индекс', max_length=20)
    city = models.CharField('Город', max_length=100)
    region = models.CharField('Страна, край, район', max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(
        'Статус', 
        max_length=20, 
        choices=OrderStatus.choices, 
        default=OrderStatus.NEW
    )
    paid = models.BooleanField('Оплачен', default=False)
    delivery_needed = models.BooleanField('Нужна доставка', default=False)
    comments = models.TextField('Комментарий к заказу', blank=True)
    
    class Meta:
        ordering = ('-created',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
    
    def __str__(self):
        return f'Заказ {self.id}'
    
    def get_full_name(self):
        """Возвращает полное ФИО"""
        full_name = f"{self.last_name} {self.first_name}"
        if self.patronymic:
            full_name += f" {self.patronymic}"
        return full_name
    
    def get_total_cost(self):
        total = 0
        for item in self.items.all():
            total += item.get_cost()
        return total

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product', related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField('Количество', default=1)
    
    def __str__(self):
        return str(self.id)
    
    def get_cost(self):
        if self.price is None or self.quantity is None:
            return 0
        return self.price * self.quantity
# Create your models here.
