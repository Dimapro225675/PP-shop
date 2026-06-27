from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'unit_price', 'quantity')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    final_statuses = (
        Order.Status.DELIVERED,
        Order.Status.CANCELLED,
        Order.Status.PAYMENT_FAILED,
    )
    admin_statuses = (
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
        Order.Status.CANCELLED,
    )
    list_display = (
        'id',
        'user',
        'status',
        'payment_status',
        'total_amount',
        'fulfillment_method',
        'delivery_cost',
        'delivery_date',
        'hidden_from_history',
        'created_at',
    )
    list_filter = ('status', 'hidden_from_history', 'created_at')
    readonly_fields = (
        'user',
        'session_key',
        'total_amount',
        'fulfillment_method',
        'delivery_cost',
        'delivery_city',
        'delivery_street',
        'delivery_house',
        'delivery_apartment',
        'delivery_entrance',
        'delivery_comment',
        'delivery_date',
        'hidden_from_history',
        'payment_id',
        'payment_status',
        'payment_confirmation_url',
        'payment_idempotence_key',
        'created_at',
    )
    search_fields = ('user__username', 'user__email', 'payment_id')
    inlines = (OrderItemInline,)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return super().has_change_permission(request, obj)
        return (
            obj.status not in self.final_statuses
            and super().has_change_permission(request, obj)
        )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in self.final_statuses:
            fields.append('status')
        return fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        status_field = form.base_fields.get('status')
        if status_field and obj:
            allowed_values = set(self.admin_statuses)
            choices = [
                choice
                for choice in Order.Status.choices
                if choice[0] in allowed_values
            ]
            if obj.status not in allowed_values:
                choices.insert(0, (obj.status, obj.get_status_display()))
            status_field.choices = choices
        return form
