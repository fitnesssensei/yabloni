#!/usr/bin/env python
import os
import django
from django.core.mail import send_mail
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_email():
    """Тестовая функция для проверки отправки email"""
    try:
        subject = 'Тестовое письмо из Яблони и Груши'
        message = '''
        Здравствуйте!
        
        Это тестовое письмо для проверки работы email-уведомлений.
        Если вы получили это письмо, значит настройки SMTP работают корректно.
        
        С уважением,
        Команда "Яблони и Груши"
        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            ['13fitnesssensei@gmail.com'],  # тестовый email
            fail_silently=False,
        )
        
        print(f"✅ Письмо успешно отправлено с {settings.DEFAULT_FROM_EMAIL}")
        print(f"📧 Настройки SMTP: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        print(f"🔒 Используется SSL: {settings.EMAIL_USE_SSL}")
        
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")
        print(f"📧 EMAIL_HOST: {settings.EMAIL_HOST}")
        print(f"🔑 EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        print(f"🔒 EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")

if __name__ == '__main__':
    test_email()
