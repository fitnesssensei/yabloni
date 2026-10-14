"""Тесты оформления заказа (orders.views.order_create).

Проверяем, что заказ оформляется и тогда, когда письмо отправить нечем: настройки
email могут быть пустыми или выключенными, а сбой SMTP не должен ломать заказ.
"""
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from catalog.models import Category, Product
from core.models import EmailSettings
from orders.models import Order, OrderItem

# Значения EMAIL_* «как на сервере»: переменных в .env нет, значит пустые. Нужны
# как override_settings, чтобы post_save-сигнал update_email_settings не изменил
# настоящие settings процесса и не «протёк» в другие тесты
EMPTY_EMAIL_SETTINGS = {
    'EMAIL_HOST_USER': '',
    'EMAIL_HOST_PASSWORD': '',
    'DEFAULT_FROM_EMAIL': '',
    'SERVER_EMAIL': '',
}


class OrderCreateTests(TestCase):
    """Оформление заказа: письмо не должно ломать сам заказ."""

    def setUp(self):
        self.url = reverse('orders:order_create')
        category = Category.objects.create(name='Яблони', slug='yabloni')
        self.product = Product.objects.create(
            name='Яблоня Антоновка',
            slug='antonovka',
            category=category,
            price=Decimal('1500.00'),
            stock=10,
        )
        # Корзина живёт в сессии: кладём позицию так, как это делает Cart.add
        session = self.client.session
        session['cart'] = {
            str(self.product.id): {
                'quantity': 2,
                'price': '1500.00',
                'season': 'Осень',
            }
        }
        session.save()

        self.form_data = {
            'full_name': 'Иванов Иван Иванович',
            'email': 'client@example.com',
            'phone': '+7 (999) 123-45-67',
            'delivery_needed': 'on',
            'region': 'Московская область',
            'city': 'Москва',
            'postal_code': '101000',
            'address': 'ул. Ленина, д. 1',
            'comments': 'Позвоните перед отправкой',
        }

    def create_email_settings(self, **overrides):
        """Создаёт единственную запись настроек email (сохраняется под pk=1)."""
        values = {
            'email_host_user': 'shop@yandex.ru',
            'email_host_password': 'app-password',
            'default_from_email': 'shop@yandex.ru',
        }
        values.update(overrides)
        with override_settings(**EMPTY_EMAIL_SETTINGS):
            return EmailSettings.objects.create(**values)

    def test_order_is_created_and_email_sent_with_db_settings(self):
        """Письмо уходит клиенту с настройками из админки, заказ сохранён."""
        self.create_email_settings()
        with patch('orders.views.build_email_connection') as build_mock:
            with patch('orders.views.send_mail') as send_mail_mock:
                response = self.client.post(self.url, self.form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order/created.html')

        # Заказ и его позиция сохранены
        order = Order.objects.get()
        self.assertEqual(order.email, 'client@example.com')
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().season, 'Осень')
        self.assertEqual(order.items.first().quantity, 2)

        # Письмо ушло на адрес клиента с настройками из БД
        send_mail_mock.assert_called_once()
        kwargs = send_mail_mock.call_args.kwargs
        self.assertEqual(kwargs['recipient_list'], ['client@example.com'])
        self.assertEqual(kwargs['from_email'], 'shop@yandex.ru')
        self.assertIn('Заказ №', kwargs['subject'])
        self.assertIs(kwargs['connection'], build_mock.return_value)
        self.assertEqual(build_mock.call_args.args[0].email_host_user, 'shop@yandex.ru')

        # В письме отрендерен шаблон: адрес клиента и состав заказа на месте
        self.assertIn('client@example.com', kwargs['html_message'])
        self.assertIn(f'Заказ №{order.id}', kwargs['html_message'])
        self.assertIn('Яблоня Антоновка', kwargs['html_message'])

        # Корзина очищена (контекст-процессор cart при рендере страницы может
        # заново создать пустой словарь корзины, поэтому проверяем содержимое)
        self.assertFalse(self.client.session.get('cart'))
        self.assertEqual(self.client.session['order_id'], order.id)

    def test_order_is_created_when_smtp_fails(self):
        """Сбой SMTP не ломает заказ, а ошибка попадает в лог приложения."""
        self.create_email_settings()
        with patch(
            'orders.views.send_mail',
            side_effect=Exception('535 Authentication failed'),
        ):
            with self.assertLogs('orders.views', level='ERROR') as logs:
                response = self.client.post(self.url, self.form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().items.count(), 1)
        self.assertTrue(
            any('535 Authentication failed' in message for message in logs.output),
            logs.output,
        )
        # Email клиента — персональные данные, в лог он попадать не должен
        self.assertFalse(
            any('client@example.com' in message for message in logs.output),
            logs.output,
        )

    def test_order_is_created_when_email_settings_are_empty(self):
        """Пустые настройки (состояние «ещё не заполнено») заказу не мешают."""
        self.create_email_settings(
            email_host_user='', email_host_password='', default_from_email=''
        )
        with patch('orders.views.send_mail') as send_mail_mock:
            with self.assertLogs('orders.views', level='WARNING') as logs:
                response = self.client.post(self.url, self.form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        send_mail_mock.assert_not_called()
        self.assertTrue(
            any('не заполнены email отправителя' in message for message in logs.output),
            logs.output,
        )

    def test_order_is_created_when_email_is_disabled(self):
        """Выключенная отправка: заказ оформляется, письмо не уходит."""
        self.create_email_settings(email_enabled=False)
        with patch('orders.views.send_mail') as send_mail_mock:
            response = self.client.post(self.url, self.form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        send_mail_mock.assert_not_called()

    def test_invalid_form_does_not_create_order_and_keeps_cart(self):
        """Невалидная форма: заказ не создан, корзина на месте."""
        self.form_data['phone'] = '123'
        response = self.client.post(self.url, self.form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/detail.html')
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn('cart', self.client.session)

    def test_repeated_post_does_not_create_second_order(self):
        """Повторная отправка формы (F5/двойной клик) не создаёт второй заказ."""
        self.create_email_settings()
        with patch('orders.views.send_mail') as send_mail_mock:
            self.client.post(self.url, self.form_data, follow=True)
            response = self.client.post(self.url, self.form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().items.count(), 1)
        # Письмо тоже уходит только одно
        send_mail_mock.assert_called_once()

    def test_post_with_empty_cart_does_not_create_order(self):
        """POST с пустой корзиной: заказа нет, покупатель возвращается в корзину."""
        session = self.client.session
        session['cart'] = {}
        session.save()

        response = self.client.post(self.url, self.form_data)

        self.assertRedirects(response, reverse('cart:cart_detail'))
        self.assertEqual(Order.objects.count(), 0)

    def test_order_created_page_requires_order_in_session(self):
        """Страница «Заказ оформлен» без заказа в сессии ведёт в корзину."""
        response = self.client.get(reverse('orders:order_created'))

        self.assertRedirects(response, reverse('cart:cart_detail'))

    def test_order_created_page_shows_saved_order(self):
        """После оформления страница «Спасибо» показывает заказ из сессии."""
        self.create_email_settings()
        with patch('orders.views.send_mail'):
            self.client.post(self.url, self.form_data, follow=True)

        response = self.client.get(reverse('orders:order_created'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/order/created.html')
        self.assertContains(response, f'<strong>{Order.objects.get().id}</strong>')
        # Письмо ушло — страница это подтверждает
        self.assertContains(response, 'отправлено письмо с подтверждением')

    def test_created_page_warns_when_email_was_not_sent(self):
        """Если письмо не ушло, страница «Спасибо» честно об этом предупреждает."""
        self.create_email_settings(email_enabled=False)
        with patch('orders.views.send_mail'):
            self.client.post(self.url, self.form_data, follow=True)

        response = self.client.get(reverse('orders:order_created'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'отправить не удалось')
        self.assertNotContains(response, 'отправлено письмо с подтверждением')

    def test_order_is_created_when_settings_cannot_be_loaded(self):
        """Сбой чтения настроек (гонка get_or_create) не ломает заказ."""
        with patch(
            'orders.views.EmailSettings.load',
            side_effect=IntegrityError('duplicate key value violates unique constraint'),
        ):
            with patch('orders.views.send_mail') as send_mail_mock:
                with self.assertLogs('orders.views', level='ERROR') as logs:
                    response = self.client.post(self.url, self.form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        send_mail_mock.assert_not_called()
        self.assertTrue(
            any('Не удалось подготовить письмо' in message for message in logs.output),
            logs.output,
        )

    def test_order_is_created_when_email_template_fails(self):
        """Сбой рендера шаблона письма: письмо уходит простым текстом, заказ цел."""
        self.create_email_settings()
        with patch(
            'orders.views.render_to_string',
            side_effect=Exception('шаблон сломан'),
        ):
            with patch('orders.views.send_mail') as send_mail_mock:
                with self.assertLogs('orders.views', level='ERROR') as logs:
                    response = self.client.post(self.url, self.form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get()
        send_mail_mock.assert_called_once()
        self.assertEqual(
            send_mail_mock.call_args.kwargs['message'],
            f'Заказ №{order.id} оформлен',
        )
        self.assertTrue(
            any('Не отрендерился шаблон письма' in message for message in logs.output),
            logs.output,
        )

    def test_created_page_sql_does_not_grow_with_items(self):
        """Запросов на странице «Спасибо» не больше от роста числа позиций (N+1)."""
        second_product = Product.objects.create(
            name='Груша Лада',
            slug='grusha-lada',
            category=self.product.category,
            price=Decimal('1200.00'),
            stock=5,
        )
        order = Order.objects.create(
            last_name='Иванов',
            first_name='Иван',
            email='client@example.com',
            phone='+79991234567',
            address='ул. Ленина, д. 1',
            postal_code='101000',
            city='Москва',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            price=Decimal('1500.00'),
            quantity=1,
            season='Осень',
        )
        session = self.client.session
        session['order_id'] = order.id
        session.save()

        with CaptureQueriesContext(connection) as one_item:
            self.client.get(reverse('orders:order_created'))

        # Вторая позиция: при N+1 появились бы дополнительные запросы
        OrderItem.objects.create(
            order=order,
            product=second_product,
            price=Decimal('1200.00'),
            quantity=1,
            season='Весна',
        )

        with CaptureQueriesContext(connection) as two_items:
            self.client.get(reverse('orders:order_created'))

        self.assertEqual(
            len(one_item.captured_queries),
            len(two_items.captured_queries),
            two_items.captured_queries,
        )
