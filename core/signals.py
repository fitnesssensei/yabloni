from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from .models import EmailSettings


@receiver(post_save, sender=EmailSettings)
def update_email_settings(sender, instance, **kwargs):
    """
    Автоматически обновляет Django settings при изменении настроек в БД.
    """
    # Обновляем настройки Django в реальном времени
    settings.EMAIL_HOST = instance.email_host
    settings.EMAIL_PORT = instance.email_port
    settings.EMAIL_USE_SSL = instance.email_use_ssl
    settings.EMAIL_USE_TLS = instance.email_use_tls
    settings.EMAIL_HOST_USER = instance.email_host_user
    settings.EMAIL_HOST_PASSWORD = instance.email_host_password
    settings.DEFAULT_FROM_EMAIL = instance.get_default_from_email()
    settings.SERVER_EMAIL = instance.get_default_from_email()


def get_email_settings():
    """
    Получает текущие настройки email из БД или возвращает None если не настроены.
    """
    try:
        return EmailSettings.objects.get(pk=1)
    except EmailSettings.DoesNotExist:
        return None


def send_test_email(to_email=None):
    """
    Отправляет тестовое письмо для проверки настроек.
    """
    email_settings = get_email_settings()
    
    if not email_settings:
        return False, "Настройки email не найдены. Сначала настройте email в админке."
    
    if not email_settings.email_enabled:
        return False, "Отправка email отключена в настройках."
    
    if not email_settings.email_host_user:
        return False, "Не указан email отправителя."
    
    if not email_settings.email_host_password:
        return False, "Не указан пароль приложения."
    
    # Email для тестирования
    test_email = to_email or email_settings.email_host_user
    
    try:
        send_mail(
            subject=f'{email_settings.email_subject_prefix} Тестовое письмо',
            message='Это тестовое письмо для проверки настроек email.\n\nЕсли вы получили это письмо, значит настройки работают корректно!',
            from_email=email_settings.get_default_from_email(),
            recipient_list=[test_email],
            fail_silently=False,
        )
        return True, f"Тестовое письмо успешно отправлено на {test_email}"
    except Exception as e:
        return False, f"Ошибка отправки: {str(e)}"
