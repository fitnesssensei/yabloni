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
from django.template.loader import render_to_string
from django.utils.html import strip_tags


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
                    quantity=item['quantity']
                )
            
            # Отладка настроек email
            print("="*50)
            print("EMAIL НАСТРОЙКИ:")
            print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
            print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
            print(f"  EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
            print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            print(f"  EMAIL_HOST_PASSWORD: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'НЕ УСТАНОВЛЕН'}")
            print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
            print("="*50)
            
            # Отправка email
            subject = f'Заказ №{order.id}'
            try:
                html_message = render_to_string('orders/order/email.html', {'order': order})
                print(f"✅ Шаблон отрендерен успешно")
            except Exception as e:
                print(f"❌ Ошибка рендеринга шаблона: {e}")
                html_message = f"Заказ №{order.id} оформлен"
            
            plain_message = strip_tags(html_message)
            from_email = settings.DEFAULT_FROM_EMAIL
            to = order.email

            print(f"📧 Попытка отправить письмо:")
            print(f"   От: {from_email}")
            print(f"   Кому: {to}")
            print(f"   Тема: {subject}")

            try:
                result = send_mail(
                    subject,
                    plain_message,
                    from_email,
                    [to],
                    html_message=html_message,
                    fail_silently=False,
                )
                print(f"✅ Письмо отправлено! Результат: {result}")
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
