from django.db import models

class Review(models.Model):
    name = models.CharField(max_length=100, blank=True, verbose_name='Имя')
    email = models.EmailField(blank=True, verbose_name='Email')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5, verbose_name='Рейтинг')
    comment = models.TextField(blank=True, verbose_name='Отзыв')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_approved = models.BooleanField(default=False, verbose_name='Одобрен')

    def __str__(self):
        return f'Отзыв от {self.name} ({self.rating} звезд)'

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
