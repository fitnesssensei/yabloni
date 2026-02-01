#!/usr/bin/env python
import os
import django
from django.core.mail import send_mail
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_gmail():
    """Тест Gmail SMTP"""
    # Временно меняем настройки на Gmail
    settings.EMAIL_HOST = 'smtp.gmail.com'
    settings.EMAIL_PORT = 587
    settings.EMAIL_USE_SSL = False
    settings.EMAIL_USE_TLS = True
    settings.EMAIL_HOST_USER = '13fitnesssensei@gmail.com'
    settings.EMAIL_HOST_PASSWORD = 'your-gmail-app-password'  # Нужно заменить
    
    try:
        send_mail(
            'Тест Gmail',
            'Тестовое сообщение через Gmail',
            settings.EMAIL_HOST_USER,
            ['13fitnesssensei@gmail.com'],
            fail_silently=False,
        )
        print("✅ Gmail работает!")
    except Exception as e:
        print(f"❌ Ошибка Gmail: {e}")

if __name__ == '__main__':
    test_gmail()
