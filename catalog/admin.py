from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.html import format_html
from .models import Category, Product, ProductImage
from .forms import ProductImageForm


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Оставляем 1 форму для добавления отдельных изображений
    fields = ['image', 'is_main']
    ordering = ['-is_main', 'created']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'available', 'stock', 'get_image_count', 'image_preview']
    list_filter = ['available', 'category', 'is_new', 'is_featured']
    list_editable = ['price', 'available', 'stock']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    change_form_template = 'admin/product_change_form.html'
    
    def get_image_count(self, obj):
        return obj.images.count()
    get_image_count.short_description = 'Кол-во изображений'
    
    def image_preview(self, obj):
        main_image = obj.get_main_image()
        if main_image:
            return format_html('<img src="{}" width="50" height="50" />', main_image.url)
        return "Нет изображения"
    image_preview.short_description = 'Превью'
    
    def response_add(self, request, obj):
        # Обработка мультизагрузки после создания товара
        if 'multiupload' in request.POST:
            form = ProductImageForm(request.POST, request.FILES)
            if form.is_valid():
                form.save_files(obj)
                self.message_user(request, 'Изображения успешно загружены!')
                return redirect(reverse('admin:catalog_product_change', args=[obj.pk]))
        return super().response_add(request, obj)
    
    def response_change(self, request, obj):
        # Обработка мультизагрузки после сохранения товара
        if 'multiupload' in request.POST:
            form = ProductImageForm(request.POST, request.FILES)
            if form.is_valid():
                form.save_files(obj)
                self.message_user(request, 'Изображения успешно загружены!')
                return redirect(reverse('admin:catalog_product_change', args=[obj.pk]))
        return super().response_change(request, obj)
# Register your models here.
