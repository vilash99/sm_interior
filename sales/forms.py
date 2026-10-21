from decimal import Decimal

from django import forms

from common.forms import INPUT_CLASS, CHECKBOX_CLASS, SELECT_CLASS
from .models import Customer, Item, PaymentTransaction, SellInvoice, SellInvoiceItem


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["name", "mrp", "is_active"]

        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'mrp': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }


class CustomerForm(forms.ModelForm):
    def clean_name(self):
        return self.cleaned_data["name"].upper()

    class Meta:
        model = Customer
        fields = ["name", "contact_number", "address", "is_active"]

        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "contact_number": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "address": forms.Textarea(
                attrs={"class": INPUT_CLASS, "rows": 3}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }


class SellInvoiceForm(forms.ModelForm):
    class Meta:
        model = SellInvoice
        fields = ["customer", "invoice_date", "notes"]
        widgets = {
            "customer": forms.Select(attrs={"class": SELECT_CLASS}),
            "invoice_date": forms.DateInput(
                attrs={"class": INPUT_CLASS, "type": "date"}
            ),
            "notes": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(
            is_active=True
        ).order_by("name")


class SellInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = SellInvoiceItem
        fields = ["item", "price", "quantity"]
        widgets = {
            "item": forms.Select(attrs={"class": SELECT_CLASS}),
            "price": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0.00", "step": "0.01"}
            ),
            "quantity": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0.01", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = Item.objects.filter(
            is_active=True
        ).order_by("name")


class PaymentTransactionForm(forms.ModelForm):
    class Meta:
        model = PaymentTransaction
        fields = [
            "invoice",
            "payment_date",
            "amount",
            "payment_mode",
            "reference_number",
            "notes",
        ]
        widgets = {
            "invoice": forms.Select(attrs={"class": SELECT_CLASS}),
            "payment_date": forms.DateInput(
                attrs={"class": INPUT_CLASS, "type": "date"}
            ),
            "amount": forms.NumberInput(
                attrs={"class": INPUT_CLASS, "min": "0.01", "step": "0.01"}
            ),
            "payment_mode": forms.Select(attrs={"class": SELECT_CLASS}),
            "reference_number": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "notes": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["invoice"].queryset = SellInvoice.objects.select_related(
            "customer"
        ).order_by("-invoice_date", "-id")
        self.fields["invoice"].required = True

    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get("invoice")
        amount = cleaned_data.get("amount")

        if not invoice or amount is None:
            return cleaned_data

        allowed_pending_amount = invoice.pending_amount
        if self.instance.pk and self.instance.invoice_id == invoice.pk:
            allowed_pending_amount += self.instance.amount or Decimal("0.00")

        if amount > allowed_pending_amount:
            self.add_error(
                "amount",
                f"Amount cannot be more than invoice pending balance ({allowed_pending_amount:.2f}).",
            )

        return cleaned_data
