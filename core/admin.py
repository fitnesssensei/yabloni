from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from .models import EmailSettings, HomeSettings, OrderInstructionsSettings
from .signals import send_test_email


@admin.register(EmailSettings)
class EmailSettingsAdmin(admin.ModelAdmin):
    """Админ-панель для настроек email"""
    
    # Отображение списка
    list_display = ['email_host_user', 'email_host', 'email_port', 'email_enabled', 'email_status']
    
    # Действия
    actions = ['send_test_email_action']
    
    # Поля для редактирования
    fieldsets = (
        ('Статус отправки', {
            'fields': ('email_enabled',),
            'description': 'Включите или выключите отправку email уведомлений'
        }),
        ('Настройки SMTP сервера', {
            'fields': ('email_host', 'email_port', 'email_use_ssl', 'email_use_tls'),
            'description': 'Настройки подключения к SMTP серверу (Yandex, Gmail и др.)'
        }),
        ('Аутентификация', {
            'fields': ('email_host_user', 'email_host_password'),
            'description': 'Внимание: используйте пароль приложения, а не пароль от почты!'
        }),
        ('Дополнительные настройки', {
            'fields': ('default_from_email', 'email_subject_prefix'),
            'description': 'Настройки отправителя и форматирования писем'
        }),
    )
    
    def email_status(self, obj):
        """Отображение статуса email.

        format_html в Django 4+ требует хотя бы один аргумент, иначе TypeError —
        без него падал весь список настроек в админке (страница отдавала 500).
        """
        if obj.email_enabled:
            return format_html('<span style="color: {};">✓ Включено</span>', 'green')
        return format_html('<span style="color: {};">✗ Отключено</span>', 'red')
    email_status.short_description = 'Статус'
    
    @admin.action(description='Отправить тестовое письмо')
    def send_test_email_action(self, request, queryset):
        """
        Action для отправки тестового письма.

        Берём настройки именно из выбранной записи, а не из settings процесса: в
        .env переменных EMAIL_* нет, поэтому в settings логин и пароль пустые, и
        письмо падало бы с ошибкой аутентификации SMTP. Получатель — адрес
        отправителя из этой же записи.
        """
        for settings_obj in queryset:
            success, message = send_test_email(email_settings=settings_obj)
            if success:
                self.message_user(request, message, messages.SUCCESS)
            else:
                self.message_user(request, message, messages.ERROR)
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Показываем пароль приложения маской, а не открытым текстом."""
        if db_field.name == 'email_host_password':
            kwargs['widget'] = forms.PasswordInput(
                render_value=True,
                attrs={'autocomplete': 'new-password'},
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def has_add_permission(self, request):
        """Запрещаем добавление новых записей (только одна запись)"""
        if EmailSettings.objects.filter(pk=1).exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление записи"""
        return False


@admin.register(HomeSettings)
class HomeSettingsAdmin(admin.ModelAdmin):
    """Админ-панель для настроек главной страницы"""
    
    # Отображение списка
    list_display = ['__str__', 'main_page_image']
    
    # Поля для редактирования
    fieldsets = (
        ('Изображение главной страницы', {
            'fields': ('main_page_image',),
            'description': 'Загрузите изображение, которое будет отображаться на главной странице в правом контейнере'
        }),
    )
    
    def has_add_permission(self, request):
        """Запрещаем добавление новых записей (только одна запись)"""
        if HomeSettings.objects.filter(pk=1).exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление записи"""
        return False


@admin.register(OrderInstructionsSettings)
class OrderInstructionsSettingsAdmin(admin.ModelAdmin):
    """Админ-панель для настроек инструкций заказов"""
    
    # Отображение списка
    list_display = ['__str__']
    
    # Поля для редактирования
    fieldsets = (
        ('Инструкции для заказов', {
            'fields': ('order_instructions',),
            'description': 'Текст инструкций, который будет показан в email уведомлении о заказе. Поддерживает HTML.'
        }),
    )
    
    def has_add_permission(self, request):
        """Запрещаем добавление новых записей (только одна запись)"""
        if OrderInstructionsSettings.objects.filter(pk=1).exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление записи"""
        return False
