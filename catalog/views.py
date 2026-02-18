
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.generic import ListView
from django.db.models import Q  # Импортируем Q для сложных запросов
from .models import Category, Product, Subcategory
from cart.forms import CartAddProductForm
from blog.models import BlogPost, News  # Импортируем модели BlogPost и News
from core.models import HomeSettings  # Импортируем HomeSettings
from faq.models import FAQ  # Импортируем модель FAQ


def product_list(request, category_slug=None, subcategory_slug=None):
    category = None
    subcategory = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        category_products = products.filter(category=category)
        # Получаем подкатегории, используемые в товарах этой категории
        subcategories = Subcategory.objects.filter(products__in=category_products).distinct()
        products = category_products
    else:
        subcategories = Subcategory.objects.none()  # Если нет категории, не показываем подкатегории
    
    if subcategory_slug:
        subcategory = get_object_or_404(Subcategory, slug=subcategory_slug)
        products = products.filter(subcategory=subcategory)
    
    return render(request, 'catalog/product/list.html', {
        'category': category,
        'subcategory': subcategory,
        'categories': categories,
        'subcategories': subcategories,
        'products': products,
        'faqs': FAQ.objects.filter(is_published=True)
    })

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    
    # Создаем список кнопок из полей продукта
    buttons = []
    for i in range(1, 11):
        text = getattr(product, f'button{i}_text')
        content = getattr(product, f'button{i}_content')
        if text:  # Показываем только кнопки с текстом
            buttons.append({'text': text, 'content': content, 'id': f'button{i}'})
    
    return render(request, 'catalog/product/detail.html', {
        'product': product, 
        'faqs': FAQ.objects.filter(is_published=True), 
        'news': News.objects.filter(is_published=True).order_by('-created_at')[:2],
        'buttons': buttons
    })

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
        ).order_by('-created')[:4]  # Берем 4 последние новинки
        
        # Добавляем последние опубликованные статьи блога
        context['blog_posts'] = BlogPost.objects.filter(
            is_published=True
        ).order_by('-created_at')[:3]  # Берем 3 последние статьи
        
        # Добавляем последние опубликованные новости
        news_items = News.objects.filter(is_published=True).order_by('-created_at')[:3]
        # Обрабатываем контент новостей для отображения списков
        processed_news = []
        for news_item in news_items:
            content_list = []
            if ';' in news_item.content:
                for point in news_item.content.split(';'):
                    clean_point = point.strip()
                    if clean_point.startswith('•'):
                        clean_point = clean_point[1:].strip()
                    if clean_point:
                        content_list.append(clean_point)
            
            processed_news.append({
                'id': news_item.id,
                'title': news_item.title,
                'content': news_item.content,
                'created_at': news_item.created_at,
                'updated_at': news_item.updated_at,
                'image': news_item.image,
                'is_list': ';' in news_item.content,
                'content_list': content_list
            })
        context['news'] = processed_news
        
        # Добавляем настройки главной страницы
        context['home_settings'] = HomeSettings.load()
        
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
        'faqs': FAQ.objects.filter(is_published=True)
    }
    
    return render(request, 'catalog/product/search_results.html', context)