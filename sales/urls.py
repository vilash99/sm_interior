from django.urls import path

from .views import (
    CustomerCreateView,
    CustomerListView,
    CustomerUpdateView,
    ItemCreateView,
    ItemListView,
    ItemUpdateView,
    PaymentTransactionCreateView,
    PaymentTransactionListView,
    PaymentTransactionUpdateView,
    SellInvoiceCreateView,
    SellInvoiceListView,
    SellInvoicePreviewView,
    SellInvoiceUpdateView,
)

app_name = 'sales'

urlpatterns = [
    path('items/', ItemListView.as_view(), name='item_list'),
    path('items/add/', ItemCreateView.as_view(), name='item_add'),
    path('items/<int:pk>/edit/', ItemUpdateView.as_view(), name='item_edit'),

    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', CustomerCreateView.as_view(), name='customer_add'),
    path('customers/<int:pk>/edit/', CustomerUpdateView.as_view(), name='customer_edit'),

    path('payments/', PaymentTransactionListView.as_view(), name='paymenttransaction_list'),
    path('payments/add/', PaymentTransactionCreateView.as_view(), name='paymenttransaction_add'),
    path('payments/<int:pk>/edit/', PaymentTransactionUpdateView.as_view(), name='paymenttransaction_edit'),

    path('invoices/', SellInvoiceListView.as_view(), name='sell_invoice_list'),
    path('invoices/add/', SellInvoiceCreateView.as_view(), name='sell_invoice_add'),
    path('invoices/<int:pk>/edit/', SellInvoiceUpdateView.as_view(), name='sell_invoice_edit'),
    path('invoices/<int:pk>/preview/', SellInvoicePreviewView.as_view(), name='sell_invoice_preview'),
]
