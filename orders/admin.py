from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, OrderStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'price', 'season', 'get_cost')
    fields = ('product', 'price', 'quantity', 'season', 'get_cost')
    
    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = 'Сумма'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_full_name', 'email', 'phone', 'get_status_colored', 'paid', 'get_total_cost', 'created')
    list_filter = ('status', 'paid', 'created')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'id')
    readonly_fields = ('created', 'updated', 'get_total_cost')
    inlines = [OrderItemInline]
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    ordering = ('-created',)
    date_hierarchy = 'created'
    list_per_page = 25
    fieldsets = (
        ('Информация о клиенте', {
            'fields': ('user', 'last_name', 'first_name', 'patronymic', 'email', 'phone')
        }),
        ('Адрес доставки', {
            'fields': ('address', 'postal_code', 'city', 'region')
        }),
        ('Статус заказа', {
            'fields': ('status', 'paid', 'comments')
        }),
        ('Служебная информация', {
            'fields': ('created', 'updated', 'get_total_cost'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_colored(self, obj):
        colors = {
            OrderStatus.NEW: '#FFA500',      # оранжевый
            OrderStatus.PROCESSING: '#1E90FF', # синий
            OrderStatus.SHIPPED: '#32CD32',   # зеленый
            OrderStatus.DELIVERED: '#228B22', # темно-зеленый
            OrderStatus.CANCELLED: '#DC143C', # красный
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_colored.short_description = 'Статус'
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status=OrderStatus.PROCESSING)
        self.message_user(request, f'{updated} заказов переведены в статус "В обработке"')
    mark_as_processing.short_description = 'Перевести в статус "В обработке"'
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status=OrderStatus.SHIPPED)
        self.message_user(request, f'{updated} заказов переведены в статус "Отправлен"')
    mark_as_shipped.short_description = 'Перевести в статус "Отправлен"'
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status=OrderStatus.DELIVERED)
        self.message_user(request, f'{updated} заказов переведены в статус "Доставлен"')
    mark_as_delivered.short_description = 'Перевести в статус "Доставлен"'
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status=OrderStatus.CANCELLED)
        self.message_user(request, f'{updated} заказов переведены в статус "Отменен"')
    mark_as_cancelled.short_description = 'Перевести в статус "Отменен"'
    
    def get_total_cost(self, obj):
        return f"{obj.get_total_cost():.2f} ₽"
    get_total_cost.short_description = 'Сумма заказа'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('items')
    
    def changelist_view(self, request, extra_context=None):
        # Добавляем статистику
        total_orders = Order.objects.count()
        new_orders = Order.objects.filter(status=OrderStatus.NEW).count()
        processing_orders = Order.objects.filter(status=OrderStatus.PROCESSING).count()
        total_revenue = sum(order.get_total_cost() for order in Order.objects.filter(paid=True))
        
        extra_context = extra_context or {}
        extra_context['total_orders'] = total_orders
        extra_context['new_orders'] = new_orders
        extra_context['processing_orders'] = processing_orders
        extra_context['total_revenue'] = f"{total_revenue:.2f} ₽"
        
        return super().changelist_view(request, extra_context)
