from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True)
    
    # добавил метод :
    def get_absolute_url(self):
        return reverse('catalog:product_list_by_category', args=[self.slug])
    # был только метод :
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(upload_to='products/', blank=True, verbose_name='Изображение')
    available = models.BooleanField(default=True, verbose_name='В наличии')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_new = models.BooleanField('Новинка', default=False, 
        help_text='Отметьте, чтобы показать этот товар в разделе Новинки')
    
    # поле загрузки изображений 
    main_image = models.ImageField(upload_to='products/%Y/%m/%d/', blank=True, verbose_name='Основное изображение')
    is_featured = models.BooleanField('Хит продаж', default=False, help_text='Отметьте, чтобы показать этот товар в разделе Хиты продаж')
   
    # добавил метод :
    def get_absolute_url(self):
        return reverse('catalog:product_detail', args=[self.id, self.slug])
    # был только метод :
    def __str__(self):
        return self.name
