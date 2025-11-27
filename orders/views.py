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
            # Отправка email
            subject = f'Заказ №{order.id}'
            html_message = render_to_string('orders/order/email.html', {'order': order})
            plain_message = strip_tags(html_message)
            from_email = '13fitnesssensei@gmail.com'
            to = order.email

            try:
                send_mail(
                    subject,
                    plain_message,
                    from_email,
                    [to],
                    html_message=html_message,
                    fail_silently=False,
                )
                print(f"Письмо отправлено на {to}")  # Логирование
            except Exception as e:
                print(f"Ошибка отправки письма: {e}")  # Логирование ошибки

            # Отладочный принт
            print("="*50)
            print("Попытка отправить письмо на:", order.email)
            print("="*50)

            # Очистка корзины
            cart.clear()
            # Сохранение заказа в сессии
            request.session['order_id'] = order.id
            # представление создания заказа
            return render(request, 'orders/order/created.html', {'order': order})
    else:
        form = OrderCreateForm()
    return render(request, 'cart/detail.html', {'order_form': form})

        # Тестовое письмо
    try:
        send_mail(
            'Тестовое письмо',
            'Это тестовое письмо из Django',
            '13fitnesssensei@gmail.com',
            ['13fitnesssensei@gmail.com'],
            fail_silently=False,
        )
        print("Тестовое письмо отправлено!")
    except Exception as e:
        print("Ошибка при отправке письма:", str(e))
    
    return render(request, 'orders/order/created.html', {'order': order})


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
