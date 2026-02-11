###### главный URL файл ######

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from catalog.views import HomeView, register
from django.views.generic import TemplateView
from . import views


# Настройка заголовка админ-панели
admin.site.site_header = 'Яблони и Груши - Администрирование'
admin.site.site_title = 'Администрирование сайта'
admin.site.index_title = 'Добро пожаловать в панель управления'


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Аутентификация
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    #path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('logout/', auth_views.LogoutView.as_view(
        template_name='registration/logged_out.html',
        next_page='home'
    ), name='logout'),
    path('register/', register, name='register'),
    
    # Приложения
    path('cart/', include('cart.urls', namespace='cart')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('catalog/', include('catalog.urls', namespace='catalog')),
    path('legal/', TemplateView.as_view(template_name='legal/legal_info.html'), name='legal_info'),
    
    # Статические страницы
    path('nursery/', TemplateView.as_view(template_name='header/nursery.html'), name='nursery'),
    path('blog/', include('blog.urls', namespace='blog')),
    #path('blog/', TemplateView.as_view(template_name='header/blog.html'), name='blog'),
    path('search/', TemplateView.as_view(template_name='header/search.html'), name='search'),
    path('account/', TemplateView.as_view(template_name='header/account.html'), name='account'),
    
    # Главная страница
    path('', HomeView.as_view(), name='home'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
