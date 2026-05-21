from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from common.models import TimeStampedModel


class ShopDetail(TimeStampedModel):
    shop_name = models.CharField(max_length=200)
    full_address = models.TextField()

    class Meta:
        verbose_name = "Shop Detail"
        verbose_name_plural = "Shop Details"
        ordering = ["-id"]

    def __str__(self):
        return self.shop_name


class Item(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Customer(TimeStampedModel):
    name = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def total_invoice_amount(self):
        return self.invoices.aggregate(
            total=models.Sum("grand_total")
        )["total"] or Decimal("0.00")

    @property
    def total_paid_amount(self):
        return self.payments.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def pending_balance(self):
        return self.total_invoice_amount - self.total_paid_amount


class SellInvoice(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(default=timezone.now)

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new and not self.invoice_number:
            self.invoice_number = ""

        super().save(*args, **kwargs)

        if is_new and not self.invoice_number:
            self.invoice_number = f"S-{self.pk}"
            super().save(update_fields=["invoice_number", "updated_at"])

    def __str__(self):
        return f"{self.invoice_number} ({self.invoice_date.strftime('%B %d, %Y')}) - {self.customer.name}"

    @property
    def paid_amount(self):
        return self.payments.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def pending_amount(self):
        return self.grand_total - self.paid_amount

    def recalculate_totals(self):
        total = self.items.aggregate(
            total=models.Sum("line_total")
        )["total"] or Decimal("0.00")

        self.subtotal = total
        self.grand_total = total
        self.save(update_fields=["subtotal", "grand_total", "updated_at"])


class SellInvoiceItem(models.Model):
    invoice = models.ForeignKey(
        SellInvoice,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="invoice_items"
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.item.mrp

        self.line_total = self.quantity * self.price
        super().save(*args, **kwargs)

        self.invoice.recalculate_totals()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalculate_totals()


class PaymentTransaction(TimeStampedModel):
    PAYMENT_MODE_CASH = "cash"
    PAYMENT_MODE_UPI = "upi"
    PAYMENT_MODE_CHEQUE = "cheque"
    PAYMENT_MODE_NEFT_RTGS = "neft_rtgs"
    PAYMENT_MODE_OTHER = "other"

    PAYMENT_MODE_CHOICES = [
        (PAYMENT_MODE_CASH, "Cash"),
        (PAYMENT_MODE_UPI, "UPI"),
        (PAYMENT_MODE_CHEQUE, "Cheque"),
        (PAYMENT_MODE_NEFT_RTGS, "NEFT/RTGS"),
        (PAYMENT_MODE_OTHER, "Other"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    invoice = models.ForeignKey(
        SellInvoice,
        on_delete=models.SET_NULL,
        related_name="payments",
        blank=True,
        null=True
    )

    payment_date = models.DateField(default=timezone.now)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES
    )

    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cheque number, UPI reference, NEFT/RTGS reference, etc."
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-payment_date", "-id"]

    def __str__(self):
        return f"{self.customer.name} - {self.amount} - {self.payment_mode}"
