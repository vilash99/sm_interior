from django.contrib import admin

from .models import Customer, Item, PaymentTransaction, SellInvoice, SellInvoiceItem, ShopDetail


@admin.register(ShopDetail)
class ShopDetailAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "upi_id", "show_upi", "show_logo", "created_at")
    search_fields = ("shop_name", "full_address")
    ordering = ("-id",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "mrp", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_number", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "contact_number", "address")
    ordering = ("name",)


@admin.register(SellInvoice)
class SellInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "customer", "invoice_date", "grand_total", "created_at")
    list_filter = ("invoice_date", "created_at")
    search_fields = ("invoice_number", "customer__name", "notes")
    autocomplete_fields = ("customer",)
    ordering = ("-invoice_date", "-id")


@admin.register(SellInvoiceItem)
class SellInvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "item", "quantity", "price", "line_total")
    list_filter = ("invoice__invoice_date",)
    search_fields = ("invoice__invoice_number", "item__name")
    autocomplete_fields = ("invoice", "item")
    ordering = ("invoice", "id")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("customer", "invoice", "payment_date", "amount", "payment_mode", "reference_number")
    list_filter = ("payment_mode", "payment_date", "created_at")
    search_fields = ("customer__name", "invoice__invoice_number", "reference_number", "notes")
    autocomplete_fields = ("customer", "invoice")
    ordering = ("-payment_date", "-id")
