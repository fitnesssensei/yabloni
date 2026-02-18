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


class Subcategory(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название подкатегории')
    slug = models.SlugField(unique=True)
    
    class Meta:
        verbose_name = 'Подкатегория'
        verbose_name_plural = 'Подкатегории'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subcategories = models.ManyToManyField(Subcategory, blank=True, related_name='products', verbose_name='Подкатегории')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    description = models.TextField(blank=True, verbose_name='Описание')
    available = models.BooleanField(default=True, verbose_name='В наличии')
    stock = models.PositiveIntegerField(default=0, verbose_name='Остаток на складе')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_new = models.BooleanField('Новинка', default=False, 
        help_text='Отметьте, чтобы показать этот товар в разделе Новинки')
    is_featured = models.BooleanField('Хит продаж', default=False, help_text='Отметьте, чтобы показать этот товар в разделе Хиты продаж')
    enable_spring_button = models.BooleanField('Показывать кнопку "Заказать на весну"', default=True, 
        help_text='Включить/выключить отображение кнопки "Заказать на весну" на странице этого товара')
    enable_autumn_button = models.BooleanField('Показывать кнопку "Заказать на осень"', default=True, 
        help_text='Включить/выключить отображение кнопки "Заказать на осень" на странице этого товара')
    
    # Поля для кнопок в левой колонке страницы товара
    button1_text = models.CharField('Текст кнопки 1', max_length=100, default='СОДЕРЖАНИЕ', blank=True)
    button1_content = models.TextField('Содержимое кнопки 1', blank=True)
    button2_text = models.CharField('Текст кнопки 2', max_length=100, default='Характеристика сорта', blank=True)
    button2_content = models.TextField('Содержимое кнопки 2', blank=True)
    button3_text = models.CharField('Текст кнопки 3', max_length=100, default='Правила выращивания', blank=True)
    button3_content = models.TextField('Содержимое кнопки 3', blank=True)
    button4_text = models.CharField('Текст кнопки 4', max_length=100, default='Подготовка к зиме', blank=True)
    button4_content = models.TextField('Содержимое кнопки 4', blank=True)
    button5_text = models.CharField('Текст кнопки 5', max_length=100, default='Болезни и вредители', blank=True)
    button5_content = models.TextField('Содержимое кнопки 5', blank=True)
    button6_text = models.CharField('Текст кнопки 6', max_length=100, default='Сбор урожая', blank=True)
    button6_content = models.TextField('Содержимое кнопки 6', blank=True)
    button7_text = models.CharField('Текст кнопки 7', max_length=100, blank=True)
    button7_content = models.TextField('Содержимое кнопки 7', blank=True)
    button8_text = models.CharField('Текст кнопки 8', max_length=100, blank=True)
    button8_content = models.TextField('Содержимое кнопки 8', blank=True)
    button9_text = models.CharField('Текст кнопки 9', max_length=100, blank=True)
    button9_content = models.TextField('Содержимое кнопки 9', blank=True)
    button10_text = models.CharField('Текст кнопки 10', max_length=100, blank=True)
    button10_content = models.TextField('Содержимое кнопки 10', blank=True)
   
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
