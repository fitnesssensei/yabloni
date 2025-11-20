from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from catalog.models import Product
from .cart import Cart
from .forms import CartAddProductForm
from orders.forms import OrderCreateForm


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product,
                 quantity=cd['quantity'],
                 update_quantity=cd['update'])
    return redirect('cart:cart_detail')

def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    
    # Создаем форму заказа
    if request.method == 'POST':
        order_form = OrderCreateForm(request.POST)
        if order_form.is_valid():
            # Создаем заказ
            order = order_form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.save()
            
            # Добавляем товары в заказ
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
            
            # Очищаем корзину
            cart.clear()
            
            # Сохраняем ID заказа в сессии
            request.session['order_id'] = order.id
            
            # Перенаправляем на страницу успешного оформления
            return render(request, 'orders/order/created.html', {'order': order})
    else:
        order_form = OrderCreateForm()
    
    # Добавляем форму обновления количества для каждого товара
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(
            initial={
                'quantity': item['quantity'],
                'update': True
            }
        )
    
    return render(
        request,
        'cart/detail.html',
        {
            'cart': cart,
            'order_form': order_form
        }
    )

    
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return redirect('cart:cart_detail')
    