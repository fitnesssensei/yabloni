#!/usr/bin/env python
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email_file_backend():
    """Тест с файловым backend для проверки логики"""
    # Временно меняем backend на файловый
    original_backend = settings.EMAIL_BACKEND
    settings.EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    settings.EMAIL_FILE_PATH = '/tmp/app-messages'
    
    try:
        subject = 'Тестовое письмо из Яблони и Груши'
        message = '''Здравствуйте!

Это тестовое письмо для проверки работы email-уведомлений.
Если вы получили это письмо, значит настройки SMTP работают корректно.

С уважением,
Команда "Яблони и Груши"'''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            ['test@example.com'],
            fail_silently=False,
        )
        
        print(f"✅ Письмо успешно 'отправлено' (сохранено в файл)")
        print(f"📁 Проверьте папку: /tmp/app-messages")
        print(f"📧 От: {settings.DEFAULT_FROM_EMAIL}")
        print(f"🔧 Backend: {settings.EMAIL_BACKEND}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        settings.EMAIL_BACKEND = original_backend

def test_smtp_settings():
    """Проверяем текущие SMTP настройки"""
    print("\n=== Текущие SMTP настройки ===")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'НЕ УСТАНОВЛЕН'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print("================================\n")

if __name__ == '__main__':
    test_smtp_settings()
    test_email_file_backend()
