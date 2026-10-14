from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
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

    def get_from_address(self):
        """
        Возвращает адрес из «От кого» без отображаемого имени.

        В поле можно писать и просто адрес, и вариант с именем:
        «Яблони и Груши <shop@yandex.ru>» → «shop@yandex.ru».
        """
        value = (self.default_from_email or '').strip()
        if value.endswith('>') and '<' in value:
            return value[value.rindex('<') + 1:-1].strip()
        return value

    def clean(self):
        """
        Проверяет настройки email перед сохранением в админке.

        Ловит ровно те причины, по которым письма не отправляются: одновременно
        включённые SSL и TLS (Django бросает ValueError при создании соединения),
        несовпадение порта и типа шифрования и «От кого» не совпадает с адресом
        отправителя — такой конверт SMTP-сервер отклоняет (у Яндекса это 553).
        """
        super().clean()
        errors = {}

        # SSL и TLS взаимоисключающие: Django бросает ValueError в get_connection
        if self.email_use_ssl and self.email_use_tls:
            errors['email_use_tls'] = ValidationError(
                'Нельзя одновременно включить SSL и TLS. Оставьте что-то одно: '
                '465 + SSL или 587 + TLS.',
                code='ssl_tls_conflict',
            )

        # Порт 587 (и 25) работает по STARTTLS — это TLS, а не SSL
        if self.email_use_ssl and self.email_port in (25, 587):
            errors['email_port'] = ValidationError(
                f'Порт {self.email_port} работает по STARTTLS: включите TLS и '
                'выключите SSL либо укажите порт 465.',
                code='ssl_wrong_port',
            )

        # Порт 465 — неявный SSL: с TLS соединение не поднимется
        if self.email_use_tls and self.email_port == 465:
            errors['email_port'] = ValidationError(
                'Порт 465 требует SSL, а не TLS: включите SSL либо укажите порт 587.',
                code='tls_wrong_port',
            )

        # «От кого» должно совпадать с логином, иначе SMTP-сервер отклонит письмо
        # (у Яндекса это ошибка 553). Приятный бонус: «пустое» здесь уже не пройдёт
        # на уровне полей, у email_host_user и email_host_password задан blank=False.
        if self.email_host_user and self.default_from_email:
            if self.get_from_address().lower() != self.email_host_user.strip().lower():
                errors['default_from_email'] = ValidationError(
                    'Адрес «От кого» должен совпадать с Email отправителя, иначе '
                    'SMTP-сервер отклонит письмо. Можно добавить отображаемое имя: '
                    'Яблони и Груши <shop@yandex.ru>.',
                    code='from_email_mismatch',
                )

        # Формат адреса проверяем прямо здесь, а не валидатором в поле: валидатор
        # в поле потребовал бы миграцию, а clean() вызывается формой админки
        if self.email_host_user:
            try:
                EmailValidator()(self.email_host_user)
            except ValidationError:
                errors['email_host_user'] = ValidationError(
                    'Укажите полный email, например shop@yandex.ru.',
                    code='invalid_sender_email',
                )

        if errors:
            raise ValidationError(errors)


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


class OrderInstructionsSettings(SingletonModel):
    """Настройки инструкций для заказов в email"""
    
    order_instructions = models.TextField(
        'Инструкции для заказов',
        blank=True,
        default='Заказ принят, ожидает оплаты. Все саженцы в наличии, замена сортов без согласования не производится.\n\nОплата на карту СберБанк xxxx xxx xxxxx xxxx на имя Андрей Александрович М.\n\nОбязательно сообщите мне о внесенной оплате на электронную почту (нажав «Ответить» на это письмо). Без этого сообщения я не смогу опознать ваш платеж и приступить к сборке. Срок оплаты заказа - 3 дня.',
        help_text='Инструкции, которые будут показаны в email уведомлении о заказе. Поддерживает HTML.'
    )
    
    class Meta:
        verbose_name = 'Email письмо'
        verbose_name_plural = 'Email письма'
    
    def __str__(self):
        return "Настройки инструкций заказов"
