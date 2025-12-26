from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class BlogPost(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('URL', max_length=200, unique=True, blank=True)
    content = models.TextField('Содержание')
    created_at = models.DateTimeField('Дата создания', default=timezone.now)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    is_published = models.BooleanField('Опубликовано', default=False)
    image = models.ImageField('Изображение', upload_to='blog/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Статья блога'
        verbose_name_plural = 'Статьи блога'
        ordering = ['-created_at']