from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True)
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории товаров'
    
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
    available = models.BooleanField(default=True, verbose_name='В наличии')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_new = models.BooleanField('Новинка', default=False, 
        help_text='Отметьте, чтобы показать этот товар в разделе Новинки')
    is_featured = models.BooleanField('Хит продаж', default=False, help_text='Отметьте, чтобы показать этот товар в разделе Хиты продаж')
   
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
    
    def get_main_image(self):
        """Возвращает основное изображение товара или первое доступное"""
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image
        first_image = self.images.first()
        return first_image.image if first_image else None
   
    # добавил метод :
    def get_absolute_url(self):
        return reverse('catalog:product_detail', args=[self.id, self.slug])
    # был только метод :
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/%Y/%m/%d/', verbose_name='Изображение')
    is_main = models.BooleanField(default=False, verbose_name='Основное изображение')
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['-is_main', 'created']
    
    def __str__(self):
        return f'Изображение для {self.product.name}'
