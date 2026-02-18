from django.contrib import admin
from .models import FAQ

# Register your models here.

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('question', 'answer')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': ('question', 'answer')
        }),
        ('Настройки публикации', {
            'fields': ('is_published',),
            'classes': ('collapse',)
        }),
    )
