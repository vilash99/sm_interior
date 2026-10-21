from base64 import b64encode
from datetime import date
from decimal import Decimal
from urllib.parse import quote, urlencode

import qrcode
from qrcode.image.svg import SvgPathFillImage

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from audit.models import log_action
from common.mixins import FormInvalidMessageMixin
from common.views import amount_to_indian_words
from accounts.mixins import PageAccessRequiredMixin

from .forms import (
    CustomerForm,
    ItemForm,
    PaymentTransactionForm,
    SellInvoiceForm,
    SellInvoiceItemForm,
)
from .models import Customer, Item, PaymentTransaction, SellInvoice, SellInvoiceItem, ShopDetail


class ItemListView(PageAccessRequiredMixin, ListView):
    model = Item
    template_name = "sales/item_list.html"
    context_object_name = "items"
    paginate_by = 25

    page_code = 'app_items'
    access_type = 'view'

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get("q", "").strip()

        if search_query:
            queryset = queryset.filter(Q(name__icontains=search_query))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        return context


class ItemCreateView(PageAccessRequiredMixin, FormInvalidMessageMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = "sales/item_form.html"

    page_code = 'app_items'
    access_type = 'edit'

    def form_valid(self, form):
        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action="create",
            instance=self.object,
            changes=form.cleaned_data,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )

        messages.success(self.request, "Item created successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("sales:item_list")


class ItemUpdateView(PageAccessRequiredMixin, FormInvalidMessageMixin, UpdateView):
    model = Item
    form_class = ItemForm
    template_name = "sales/item_form.html"

    page_code = 'app_items'
    access_type = 'edit'

    def form_valid(self, form):
        old_instance = self.get_object()
        changed_fields = {}

        for field in form.changed_data:
            old_value = getattr(old_instance, field)
            new_value = form.cleaned_data.get(field)
            changed_fields[field] = {
                "old": str(old_value),
                "new": str(new_value),
            }

        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action="update",
            instance=self.object,
            changes=changed_fields,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )

        messages.success(self.request, "Item updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("sales:item_list")


class CustomerListView(PageAccessRequiredMixin, ListView):
    model = Customer
    template_name = "sales/customer_list.html"
    context_object_name = "customers"
    paginate_by = 25

    page_code = "app_customers"
    access_type = "view"

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get("q", "").strip()

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(contact_number__icontains=search_query)
                | Q(address__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        return context


class CustomerCreateView(PageAccessRequiredMixin, FormInvalidMessageMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "sales/customer_form.html"

    page_code = "app_customers"
    access_type = "edit"

    def form_valid(self, form):
        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action="create",
            instance=self.object,
            changes=form.cleaned_data,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )

        messages.success(self.request, "Customer created successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("sales:customer_list")


class CustomerUpdateView(PageAccessRequiredMixin, FormInvalidMessageMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "sales/customer_form.html"

    page_code = "app_customers"
    access_type = "edit"

    def form_valid(self, form):
        old_instance = self.get_object()
        changed_fields = {}

        for field in form.changed_data:
            old_value = getattr(old_instance, field)
            new_value = form.cleaned_data.get(field)
            changed_fields[field] = {
                "old": str(old_value),
                "new": str(new_value),
            }

        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action="update",
            instance=self.object,
            changes=changed_fields,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )

        messages.success(self.request, "Customer updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("sales:customer_list")


class PaymentTransactionListView(PageAccessRequiredMixin, ListView):
    model = PaymentTransaction
    template_name = "sales/payment_transaction_list.html"
    context_object_name = "payments"
    paginate_by = 25

    page_code = "app_payments"
    access_type = "view"

    @cached_property
    def date_filters(self):
        today = timezone.localdate()
        dates = {}
        for name in ("start_date", "end_date"):
            value = self.request.GET.get(name, "").strip()
            try:
                dates[name] = date.fromisoformat(value)
            except ValueError:
                dates[name] = today
        return dates

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer", "invoice")
        queryset = queryset.filter(
            payment_date__gte=self.date_filters["start_date"],
            payment_date__lte=self.date_filters["end_date"],
        )
        search_query = self.request.GET.get("q", "").strip()

        if search_query:
            queryset = queryset.filter(
                Q(customer__name__icontains=search_query)
                | Q(invoice__invoice_number__icontains=search_query)
                | Q(reference_number__icontains=search_query)
                | Q(payment_mode__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context.update({name: value.isoformat() for name, value in self.date_filters.items()})
        return context


class PaymentTransactionCreateView(PageAccessRequiredMixin, FormInvalidMessageMixin, CreateView):
    model = PaymentTransaction
    form_class = PaymentTransactionForm
    template_name = "sales/payment_transaction_form.html"

    page_code = "app_payments"
    access_type = "edit"

    def form_valid(self, form):
        form.instance.customer = form.cleaned_data["invoice"].customer
        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action="create",
            instance=self.object,
            changes=form.cleaned_data,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )

        messages.success(self.request, "Payment transaction created successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("sales:paymenttransaction_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice_pending_map"] = self.get_invoice_pending_map()
        return context

    def get_invoice_pending_map(self):
        return {
            str(invoice.pk): str(invoice.pending_amount)
            for invoice in SellInvoice.objects.select_related("customer").order_by("-invoice_date", "-id")
        }


class PaymentTransactionUpdateView(PageAccessRequiredMixin, FormInvalidMessageMixin, UpdateView):
    model = PaymentTransaction
    form_class = PaymentTransactionForm
    template_name = "sales/payment_transaction_form.html"

    page_code = "app_payments"
    access_type = "edit"

    def form_valid(self, form):
        old_instance = self.get_object()
        changed_fields = {}

        for field in form.changed_data:
            old_value = getattr(old_instance, field)
            new_value = form.cleaned_data.get(field)
            changed_fields[field] = {
                "old": str(old_value),
                "new": str(new_value),
            }

        new_customer = form.cleaned_data["invoice"].customer
        if old_instance.customer != new_customer:
            changed_fields["customer"] = {
                "old": str(old_instance.customer),
                "new": str(new_customer),
            }

        form.instance.customer = new_customer

        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action="update",
            instance=self.object,
            changes=changed_fields,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )

        messages.success(self.request, "Payment transaction updated successfully.")
        return response

    def get_success_url(self):
        return reverse_lazy("sales:paymenttransaction_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice_pending_map"] = self.get_invoice_pending_map()
        return context

    def get_invoice_pending_map(self):
        invoice_pending_map = {}
        for invoice in SellInvoice.objects.select_related("customer").order_by("-invoice_date", "-id"):
            pending_amount = invoice.pending_amount
            if self.object and self.object.invoice_id == invoice.pk:
                pending_amount += self.object.amount or Decimal("0.00")
            invoice_pending_map[str(invoice.pk)] = str(pending_amount)
        return invoice_pending_map


class SellInvoiceCreateView(PageAccessRequiredMixin, FormInvalidMessageMixin, CreateView):
    model = SellInvoice
    form_class = SellInvoiceForm
    template_name = "sales/sell_invoice_form.html"

    page_code = "app_sell_invoices"
    access_type = "edit"

    def form_valid(self, form):
        response = super().form_valid(form)

        log_action(
            user=self.request.user,
            action="create",
            instance=self.object,
            changes=form.cleaned_data,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )

        messages.success(
            self.request,
            "Invoice created successfully. You can add invoice items now.",
        )
        return response

    def get_success_url(self):
        return reverse_lazy("sales:sell_invoice_edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice_items"] = []
        context["invoice_item_form"] = SellInvoiceItemForm()
        context["editing_invoice_item"] = None
        context["item_price_map"] = self.get_item_price_map()
        return context

    def get_item_price_map(self):
        return {
            str(item.pk): str(item.mrp)
            for item in Item.objects.filter(is_active=True).order_by("name")
        }


class SellInvoiceListView(PageAccessRequiredMixin, ListView):
    model = SellInvoice
    template_name = "sales/sell_invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25

    page_code = "app_sell_invoices"
    access_type = "view"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer")
        search_query = self.request.GET.get("q", "").strip()
        start_date = self.request.GET.get("start_date", "").strip()
        end_date = self.request.GET.get("end_date", "").strip()

        if search_query:
            queryset = queryset.filter(customer__name__icontains=search_query)

        if start_date:
            queryset = queryset.filter(invoice_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(invoice_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()

        context["search_query"] = self.request.GET.get("q", "").strip()
        context["start_date"] = self.request.GET.get("start_date", "").strip()
        context["end_date"] = self.request.GET.get("end_date", "").strip()
        context["filtered_total_amount"] = (
            filtered_queryset.aggregate(total=Sum("grand_total"))["total"] or 0
        )
        return context


class SellInvoicePreviewView(PageAccessRequiredMixin, DetailView):
    model = SellInvoice
    template_name = "sales/sell_invoice_preview.html"
    context_object_name = "invoice"

    page_code = "app_sell_invoices"
    access_type = "view"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_items = self.object.items.select_related("item").all()
        total_quantity = invoice_items.aggregate(total=Sum("quantity"))["total"] or Decimal("0.00")

        context["invoice_items"] = invoice_items
        context["total_quantity"] = total_quantity
        context["amount_in_words"] = amount_to_indian_words(self.object.grand_total)

        shop_detail = ShopDetail.objects.order_by("-id").first()

        context["shop_detail"] = shop_detail
        upi_id = shop_detail.upi_id.strip() if shop_detail else ""

        if shop_detail and shop_detail.show_upi and upi_id and self.object.grand_total > 0:
            payment_uri = "upi://pay?" + urlencode({
                "pa": upi_id,
                "pn": shop_detail.shop_name,
                "tr": self.object.invoice_number,
                "am": format(self.object.grand_total, ".2f"),
                "cu": "INR",
            }, quote_via=quote)
            qr_image = qrcode.make(payment_uri, image_factory=SvgPathFillImage, border=4)
            svg_data = b64encode(qr_image.to_string()).decode("ascii")
            context["upi_qr_code"] = f"data:image/svg+xml;base64,{svg_data}"
            context["upi_id"] = upi_id
        return context


class SellInvoiceUpdateView(PageAccessRequiredMixin, FormInvalidMessageMixin, UpdateView):
    model = SellInvoice
    form_class = SellInvoiceForm
    template_name = "sales/sell_invoice_form.html"

    page_code = "app_sell_invoices"
    access_type = "edit"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        editing_invoice_item = self.get_editing_invoice_item()

        context["invoice_items"] = self.object.items.select_related("item").all()
        context["invoice_item_form"] = kwargs.get("invoice_item_form") or self.get_invoice_item_form(
            editing_invoice_item
        )
        context["editing_invoice_item"] = editing_invoice_item
        context["item_price_map"] = self.get_item_price_map()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action", "save_invoice")

        if action == "save_invoice":
            return super().post(request, *args, **kwargs)

        if action == "save_invoice_item":
            return self.handle_invoice_item_submit()

        if action == "delete_invoice_item":
            return self.handle_invoice_item_delete()

        messages.error(request, "Invalid action.")
        return redirect(self.get_success_url())

    def form_valid(self, form):
        old_instance = self.get_object()
        changed_fields = {}

        for field in form.changed_data:
            old_value = getattr(old_instance, field)
            new_value = form.cleaned_data.get(field)
            changed_fields[field] = {
                "old": str(old_value),
                "new": str(new_value),
            }

        response = super().form_valid(form)

        if changed_fields:
            log_action(
                user=self.request.user,
                action="update",
                instance=self.object,
                changes=changed_fields,
                extra={"ip": self.request.META.get("REMOTE_ADDR")},
            )
            messages.success(self.request, "Invoice updated successfully.")
        else:
            messages.info(self.request, "No changes were made to the invoice.")

        return response

    def get_success_url(self):
        return reverse_lazy("sales:sell_invoice_edit", kwargs={"pk": self.object.pk})

    def get_editing_invoice_item(self):
        edit_item_id = self.request.GET.get("edit_item") or self.request.POST.get(
            "invoice_item_id"
        )
        if not edit_item_id:
            return None

        return get_object_or_404(
            SellInvoiceItem,
            pk=edit_item_id,
            invoice=self.object,
        )

    def get_invoice_item_form(self, invoice_item=None):
        if self.request.method == "POST" and self.request.POST.get("action") == "save_invoice_item":
            return SellInvoiceItemForm(self.request.POST, instance=invoice_item)
        return SellInvoiceItemForm(instance=invoice_item)

    def get_item_price_map(self):
        return {
            str(item.pk): str(item.mrp)
            for item in Item.objects.filter(is_active=True).order_by("name")
        }

    def handle_invoice_item_submit(self):
        invoice_item = None
        invoice_item_id = self.request.POST.get("invoice_item_id")

        if invoice_item_id:
            invoice_item = get_object_or_404(
                SellInvoiceItem,
                pk=invoice_item_id,
                invoice=self.object,
            )

        form = SellInvoiceItemForm(self.request.POST, instance=invoice_item)

        if not form.is_valid():
            messages.error(self.request, "Please correct the invoice item errors.")
            return self.render_to_response(
                self.get_context_data(invoice_item_form=form)
            )

        changed_fields = {}
        if invoice_item is not None:
            for field in form.changed_data:
                old_value = getattr(invoice_item, field)
                new_value = form.cleaned_data.get(field)
                changed_fields[field] = {
                    "old": str(old_value),
                    "new": str(new_value),
                }

            changed_fields["line_total"] = {
                "old": str(invoice_item.line_total),
                "new": str(form.cleaned_data["price"] * form.cleaned_data["quantity"]),
            }

        invoice_item = form.save(commit=False)
        invoice_item.invoice = self.object
        invoice_item.save()

        if self.request.POST.get("invoice_item_id"):
            log_action(
                user=self.request.user,
                action="update",
                instance=invoice_item,
                changes=changed_fields,
                extra={"ip": self.request.META.get("REMOTE_ADDR")},
            )
            messages.success(self.request, "Invoice item updated successfully.")
        else:
            log_action(
                user=self.request.user,
                action="create",
                instance=invoice_item,
                changes={
                    "item": form.cleaned_data["item"],
                    "quantity": form.cleaned_data["quantity"],
                    "price": invoice_item.price,
                    "line_total": invoice_item.line_total,
                },
                extra={"ip": self.request.META.get("REMOTE_ADDR")},
            )
            messages.success(self.request, "Invoice item added successfully.")

        return redirect(self.get_success_url())

    def handle_invoice_item_delete(self):
        invoice_item = get_object_or_404(
            SellInvoiceItem,
            pk=self.request.POST.get("invoice_item_id"),
            invoice=self.object,
        )

        deleted_snapshot = {
            "item": str(invoice_item.item),
            "quantity": str(invoice_item.quantity),
            "price": str(invoice_item.price),
            "line_total": str(invoice_item.line_total),
        }
        invoice_item.delete()

        log_action(
            user=self.request.user,
            action="delete",
            instance=invoice_item,
            changes=deleted_snapshot,
            extra={"ip": self.request.META.get("REMOTE_ADDR")},
        )
        messages.success(self.request, "Invoice item deleted successfully.")
        return redirect(self.get_success_url())
