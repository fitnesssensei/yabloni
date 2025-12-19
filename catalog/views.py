
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.generic import ListView
from django.db.models import Q  # Импортируем Q для сложных запросов
from .models import Category, Product
from cart.forms import CartAddProductForm


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    return render(request, 'catalog/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products
    })

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    return render(request, 'catalog/product/detail.html', {'product': product})

class HomeView(ListView):
    model = Product
    template_name = 'home.html'
    context_object_name = 'featured_products'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['cart_product_form'] = CartAddProductForm()
        # Добавляем новинки в контекст
        context['new_products'] = Product.objects.filter(
            is_new=True, 
            available=True
        ).order_by('-created')[:4]  # Берем 8 последних новинок
        return context

    def get_queryset(self):
            # Возвращаем только товары, отмеченные как хиты продаж
            return Product.objects.filter(is_featured=True, available=True)[:8]  # Ограничиваем количество

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Автоматический вход после регистрации
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def home(request):
    featured_products = Product.objects.filter(is_featured=True, available=True)[:10]  # Ограничиваем количество
    return render(request, 'home.html', {
        'featured_products': featured_products,
        # ... другие переменные контекста
    })


#def product_search(request):
    """
    Обработчик поисковых запросов.
    Ищет товары по названию, категории и описанию.
    """
    query = request.GET.get('q', '').strip()  # Получаем поисковый запрос из GET-параметра 'q'
    
    # Если запрос пустой, показываем все доступные товары
    if not query:
        products = Product.objects.filter(available=True)
    else:
        # Ищем по названию (регистронезависимый поиск)
        products = Product.objects.filter(
            models.Q(name__icontains=query) |  # поиск в названии
            models.Q(description__icontains=query) |  # поиск в описании
            models.Q(category__name__icontains=query),  # поиск по названию категории
            available=True  # только доступные товары
        ).distinct()  # убираем дубликаты
    
    # Получаем все категории для отображения в сайдбаре
    categories = Category.objects.all()
    
    # Создаем контекст для шаблона
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'cart_product_form': CartAddProductForm(),  # форма для добавления в корзину
    }
    
    # Рендерим шаблон с результатами поиска
    return render(request, 'catalog/product/search_results.html', context)


def product_search(request):
    query = request.GET.get('q', '').strip()
    
    if not query:
        products = Product.objects.filter(available=True)
    else:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query),
            available=True
        ).distinct()
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'cart_product_form': CartAddProductForm(),
    }
    
    return render(request, 'catalog/product/search_results.html', context)