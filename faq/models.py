from django.db import models
from django.db.models import Q

# Create your models here.

class FAQ(models.Model):
    question = models.CharField(max_length=255, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    category = models.ForeignKey('catalog.Category', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='faqs', verbose_name='Категория',
        help_text='Необязательно. Вопрос будет показан на страницах товаров этой категории')
    subcategory = models.ForeignKey('catalog.Subcategory', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='faqs', verbose_name='Подкатегория',
        help_text='Необязательно. Вопрос будет показан на страницах товаров этой подкатегории')
    is_published = models.BooleanField(default=True, verbose_name='Опубликовано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Часто задаваемый вопрос'
        verbose_name_plural = 'Часто задаваемые вопросы'
        ordering = ['-created_at']

    def __str__(self):
        return self.question

    @classmethod
    def get_for_product(cls, product):
        """Вопросы для страницы товара: по категории, подкатегориям товара
        или общие (без привязки)."""
        return cls.objects.filter(is_published=True).filter(
            Q(category=product.category) |
            Q(subcategory__in=product.subcategories.all()) |
            Q(category__isnull=True, subcategory__isnull=True)
        ).distinct()
