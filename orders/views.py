import logging

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import HttpResponse
import weasyprint

from .models import Order, OrderItem
from .forms import OrderCreateForm
from cart.cart import Cart

from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.models import EmailSettings, OrderInstructionsSettings
from core.signals import build_email_connection

# Логгер приложения: причина неотправленного письма должна быть видна в логах
# сервера, а не только в консоли разработчика
logger = logging.getLogger(__name__)

# Шаблон письма клиенту о новом заказе
ORDER_EMAIL_TEMPLATE = 'orders/order/email.html'


def send_order_email(order):
    """
    Отправляет клиенту письмо о новом заказе.

    Возвращает (True, пояснение) или (False, причина). Исключения наружу не
    выпускаем: неотправленное письмо не должно ломать оформление заказа, но
    причина обязательно попадает в лог.
    """
    email_settings = EmailSettings.load()

    if not email_settings.email_enabled:
        return False, 'Отправка email отключена в настройках админки.'

    if not email_settings.email_host_user or not email_settings.email_host_password:
        # Именно так выглядит состояние «настройки ещё не заполнены»: отправлять нечем
        return False, (
            'В настройках email не заполнены email отправителя или пароль '
            'приложения — письмо отправить невозможно.'
        )

    subject = f'{email_settings.email_subject_prefix} Заказ №{order.id}'
    from_email = email_settings.get_default_from_email()
    order_instructions_settings = OrderInstructionsSettings.load()

    try:
        html_message = render_to_string(
            ORDER_EMAIL_TEMPLATE,
            {
                'order': order,
                'order_instructions_settings': order_instructions_settings,
            },
        )
    except Exception:
        logger.exception('Не отрендерился шаблон письма о заказе №%s', order.id)
        html_message = f'Заказ №{order.id} оформлен'

    plain_message = strip_tags(html_message)

    try:
        connection = build_email_connection(email_settings)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[order.email],
            html_message=html_message,
            fail_silently=False,
            connection=connection,
        )
    except Exception as error:
        logger.exception(
            'Не отправлено письмо о заказе №%s на %s (%s:%s): %s',
            order.id,
            order.email,
            email_settings.email_host,
            email_settings.email_port,
            error,
        )
        return False, f'Ошибка отправки письма: {error}'

    return True, f'Письмо о заказе №{order.id} отправлено на {order.email}.'


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            # Заказ и его позиции сохраняем одной транзакцией: если что-то упадёт,
            # в базе не останется «полузаказа» без позиций
            with transaction.atomic():
                order = form.save()
                for item in cart:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['quantity'],
                        season=item['season']
                    )

            # Письмо уходит уже после сохранения заказа: сбой отправки не должен
            # ломать оформление, а его причина попадает в лог
            sent, reason = send_order_email(order)
            if sent:
                logger.info(reason)
            else:
                logger.warning('Письмо о заказе №%s не отправлено: %s', order.id, reason)

            # Очистка корзины
            cart.clear()
            # Сохранение заказа в сессии
            request.session['order_id'] = order.id
            return render(request, 'orders/order/created.html', {'order': order})
    else:
        form = OrderCreateForm()
    return render(request, 'cart/detail.html', {'order_form': form})


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin/orders/order/detail.html', {'order': order})

@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string('orders/order/pdf.html', {'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=order_{order.id}.pdf'
    weasyprint.HTML(string=html).write_pdf(response)
    return response
