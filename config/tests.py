"""Тесты настроек доступа по домену (ALLOWED_HOSTS).

Пустой ALLOWED_HOSTS в продакшене (DEBUG = False) приводит к ответу 400 на все
запросы: сайт и sitemap.xml становятся недоступны для поисковых роботов.
Здесь проверяем, что прод-домены и локальные хосты разрешены, а чужие — нет.
"""
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

# Хост, который отдаётся в проде (без www) — основной адрес сайта
PRODUCTION_HOST = 'yablonigrushi.ru'
# Локальные адреса, с которых запускается dev-сервер (python manage.py runserver)
LOCAL_HOSTS = ('localhost', '127.0.0.1', '[::1]')
# Лёгкая страница без обращений к БД: форма входа рендерится на пустой базе
TEST_URL = '/login/'


class AllowedHostsSettingsTests(SimpleTestCase):
    """Проверяем итоговое значение настройки ALLOWED_HOSTS."""

    def test_production_domains_are_allowed(self):
        """Прод-домены сайта (с www и без) должны быть разрешены."""
        self.assertIn(PRODUCTION_HOST, settings.ALLOWED_HOSTS)
        self.assertIn(f'www.{PRODUCTION_HOST}', settings.ALLOWED_HOSTS)

    def test_local_hosts_are_allowed(self):
        """Локальные адреса нужны, чтобы runserver отвечал в разработке."""
        for host in LOCAL_HOSTS:
            self.assertIn(host, settings.ALLOWED_HOSTS)

    def test_hosts_have_no_spaces_or_empty_values(self):
        """Значение из .env может содержать пробелы: 'site.ru, www.site.ru'."""
        for host in settings.ALLOWED_HOSTS:
            self.assertTrue(host, 'В ALLOWED_HOSTS попал пустой элемент')
            self.assertNotIn(' ', host)


class AllowedHostsRequestTests(TestCase):
    """Проверяем реальное поведение: чужие хосты отбиваются кодом 400.

    SECURE_SSL_REDIRECT отключён, чтобы 301-редирект на HTTPS (он включён при
    DEBUG = False) не подменял проверяемый ответ. Используем TestCase, а не
    SimpleTestCase: страница входа обращается к сессиям (таблица в БД).
    """

    def test_production_domain_gets_response(self):
        with override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False):
            response = self.client.get(TEST_URL, HTTP_HOST=PRODUCTION_HOST)
        self.assertEqual(response.status_code, 200)

    def test_www_domain_gets_response(self):
        with override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False):
            response = self.client.get(TEST_URL, HTTP_HOST=f'www.{PRODUCTION_HOST}')
        self.assertEqual(response.status_code, 200)

    def test_unknown_host_is_rejected(self):
        """Запрос с чужим заголовком Host должен получать 400 (защита от host injection)."""
        with override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False):
            response = self.client.get(TEST_URL, HTTP_HOST='evil.example.com')
        self.assertEqual(response.status_code, 400)
