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

from django.core.mail import send_mail, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from core.models import EmailSettings, OrderInstructionsSettings


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        print(f"\n{'='*50}")
        print(f"📥 POST запрос получен!")
        print(f"   Данные: {request.POST}")
        print(f"{'='*50}\n")
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity'],
                    season=item['season']
                )
            
            # Получаем настройки email из админки
            email_settings = EmailSettings.load()
            
            # Получаем настройки инструкций заказов
            order_instructions_settings = OrderInstructionsSettings.load()
            
            # Отладка настроек email
            print("="*50)
            print("EMAIL НАСТРОЙКИ (из админки):")
            if email_settings:
                print(f"  EMAIL_HOST: {email_settings.email_host}")
                print(f"  EMAIL_PORT: {email_settings.email_port}")
                print(f"  EMAIL_USE_SSL: {email_settings.email_use_ssl}")
                print(f"  EMAIL_HOST_USER: {email_settings.email_host_user}")
                print(f"  EMAIL_HOST_PASSWORD: {'*' * len(email_settings.email_host_password) if email_settings.email_host_password else 'НЕ УСТАНОВЛЕН'}")
                print(f"  DEFAULT_FROM_EMAIL: {email_settings.get_default_from_email()}")
                print(f"  EMAIL_ENABLED: {email_settings.email_enabled}")
            else:
                print("  Настройки email не найдены в админке!")
            print("="*50)
            
            # Проверяем, включена ли отправка email
            if not email_settings or not email_settings.email_enabled:
                print("❌ Отправка email отключена в настройках админки")
            else:
                # Отправка email
                subject = f'{email_settings.email_subject_prefix} Заказ №{order.id}'
                try:
                    html_message = render_to_string('orders/order/email.html', {'order': order, 'order_instructions_settings': order_instructions_settings})
                    print(f"✅ Шаблон отрендерен успешно")
                except Exception as e:
                    print(f"❌ Ошибка рендеринга шаблона: {e}")
                    html_message = f"Заказ №{order.id} оформлен"
                
                plain_message = strip_tags(html_message)
                from_email = email_settings.get_default_from_email()
                to = order.email

                print(f"📧 Попытка отправить письмо:")
                print(f"   От: {from_email}")
                print(f"   Кому: {to}")
                print(f"   Тема: {subject}")

                try:
                    # Создаем SMTP соединение с настройками из админки
                    connection = get_connection(
                        host=email_settings.email_host,
                        port=email_settings.email_port,
                        username=email_settings.email_host_user,
                        password=email_settings.email_host_password,
                        use_ssl=email_settings.email_use_ssl,
                        use_tls=email_settings.email_use_tls,
                    )
                    
                    send_mail(
                        subject,
                        plain_message,
                        from_email,
                        [to],
                        html_message=html_message,
                        fail_silently=False,
                        connection=connection,
                    )
                    print(f"✅ Письмо отправлено! Результат: отправлено")
                except Exception as e:
                    print(f"❌ Ошибка отправки письма: {e}")
                    import traceback
                    traceback.print_exc()

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
