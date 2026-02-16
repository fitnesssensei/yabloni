from django.db import models


class SingletonModel(models.Model):
    """Базовая модель для singleton паттерна (только одна запись в БД)"""
    
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class EmailSettings(SingletonModel):
    """Настройки email для отправки уведомлений"""
    
    # SMTP сервер
    email_host = models.CharField(
        'SMTP сервер',
        max_length=255,
        default='smtp.yandex.ru',
        help_text='Например: smtp.yandex.ru, smtp.gmail.com'
    )
    email_port = models.PositiveIntegerField(
        'Порт SMTP',
        default=465,
        help_text='Обычно 465 для SSL, 587 для TLS'
    )
    email_use_ssl = models.BooleanField(
        'Использовать SSL',
        default=True,
        help_text='Включить SSL-шифрование'
    )
    email_use_tls = models.BooleanField(
        'Использовать TLS',
        default=False,
        help_text='Включить TLS-шифрование'
    )
    
    # Аутентификация
    email_host_user = models.CharField(
        'Email отправителя',
        max_length=255,
        default='',
        help_text='Полный email адрес (например: shop@yandex.ru)'
    )
    email_host_password = models.CharField(
        'Пароль приложения',
        max_length=255,
        default='',
        help_text='Пароль приложения (не пароль от почты!)'
    )
    default_from_email = models.CharField(
        'Email "От кого"',
        max_length=255,
        default='',
        blank=True,
        help_text='Если пусто, используется Email отправителя'
    )
    
    # Дополнительные настройки
    email_subject_prefix = models.CharField(
        'Префикс темы письма',
        max_length=100,
        default='[Яблони и Груши]',
        help_text='Префикс в теме всех писем'
    )
    
    # Включение/выключение отправки
    email_enabled = models.BooleanField(
        'Включить отправку email',
        default=True,
        help_text='Отключите для тестирования без реальной отправки писем'
    )
    
    class Meta:
        verbose_name = 'Настройки email'
        verbose_name_plural = 'Настройки email'
    
    def __str__(self):
        return f"Email настройки ({self.email_host_user or 'не настроено'})"
    
    def get_default_from_email(self):
        """Возвращает email отправителя"""
        return self.default_from_email or self.email_host_user


class HomeSettings(SingletonModel):
    """Настройки главной страницы"""
    
    main_page_image = models.ImageField(
        'Изображение на главной странице',
        upload_to='home/',
        blank=True,
        null=True,
        help_text='Изображение, которое отображается в правом контейнере главной страницы'
    )
    
    class Meta:
        verbose_name = 'Настройки главной страницы'
        verbose_name_plural = 'Настройки главной страницы'
    
    def __str__(self):
        return "Настройки главной страницы"
