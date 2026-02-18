from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.html import format_html
from .models import Category, Product, ProductImage, Subcategory
from .forms import ProductImageForm
from django import forms


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'subcategories': forms.CheckboxSelectMultiple(),
        }


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Оставляем 1 форму для добавления отдельных изображений
    fields = ['image', 'is_main']
    ordering = ['-is_main', 'created']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ['name', 'category', 'get_subcategories', 'price', 'available', 'stock', 'enable_spring_button', 'enable_autumn_button', 'get_image_count', 'image_preview']
    list_filter = ['available', 'category', 'is_new', 'is_featured', 'enable_spring_button', 'enable_autumn_button']
    list_editable = ['price', 'available', 'stock', 'enable_spring_button', 'enable_autumn_button']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'subcategories', 'price', 'description', 'available', 'stock', 'is_new', 'is_featured', 'enable_spring_button', 'enable_autumn_button')
        }),
        ('Кнопки в левой колонке', {
            'fields': (
                ('button1_text', 'button1_content'),
                ('button2_text', 'button2_content'),
                ('button3_text', 'button3_content'),
                ('button4_text', 'button4_content'),
                ('button5_text', 'button5_content'),
                ('button6_text', 'button6_content'),
                ('button7_text', 'button7_content'),
                ('button8_text', 'button8_content'),
                ('button9_text', 'button9_content'),
                ('button10_text', 'button10_content'),
            ),
        }),
    )
    
    def get_image_count(self, obj):
        return obj.images.count()
    def get_subcategories(self, obj):
        return ", ".join([s.name for s in obj.subcategories.all()])
    get_subcategories.short_description = 'Подкатегории'
    
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
