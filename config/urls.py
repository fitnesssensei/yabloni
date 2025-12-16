"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
###### главный URL файл ######

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from catalog.views import HomeView, register


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
    
    # Статические страницы
    path('nursery/', TemplateView.as_view(template_name='nursery.html'), name='nursery'),
    path('blog/', TemplateView.as_view(template_name='blog.html'), name='blog'),
    path('search/', TemplateView.as_view(template_name='search.html'), name='search'),
    path('account/', TemplateView.as_view(template_name='account.html'), name='account'),
    
    # Главная страница
    path('', HomeView.as_view(), name='home'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
