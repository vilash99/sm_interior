from decimal import Decimal
import calendar
from datetime import date

from accounts.mixins import PageAccessRequiredMixin
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, ExtractMonth
from django.views.generic import TemplateView

from sales.models import Customer, PaymentTransaction, SellInvoice


class DashboardPageView(PageAccessRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    page_code = 'app_items'
    access_type = 'view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_year = date.today().year
        available_years = [dt.year for dt in SellInvoice.objects.dates("invoice_date", "year", order="DESC")]
        if current_year not in available_years:
            available_years.insert(0, current_year)

        selected_year = self.get_selected_year(available_years, current_year)
        yearly_invoices = SellInvoice.objects.filter(invoice_date__year=selected_year)
        yearly_payments = PaymentTransaction.objects.filter(payment_date__year=selected_year)

        monthly_sales = (
            yearly_invoices.annotate(month=ExtractMonth("invoice_date"))
            .values("month")
            .annotate(total=Coalesce(Sum("grand_total"), Value(Decimal("0.00"))))
            .order_by("month")
        )
        month_map = {row["month"]: row["total"] for row in monthly_sales}

        monthly_chart = [
            {
                "label": calendar.month_abbr[month],
                "value": float(month_map.get(month, Decimal("0.00"))),
            }
            for month in range(1, 13)
        ]

        total_sales = yearly_invoices.aggregate(
            total=Coalesce(Sum("grand_total"), Value(Decimal("0.00")))
        )["total"]
        total_paid = yearly_payments.aggregate(
            total=Coalesce(Sum("amount"), Value(Decimal("0.00")))
        )["total"]
        total_balance = total_sales - total_paid

        recent_invoices = (
            SellInvoice.objects.select_related("customer")
            .annotate(
                paid_amount_calc=Coalesce(Sum("payments__amount"), Value(Decimal("0.00"))),
                pending_amount_calc=ExpressionWrapper(
                    F("grand_total") - Coalesce(Sum("payments__amount"), Value(Decimal("0.00"))),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            )
            .order_by("-invoice_date", "-id")[:8]
        )

        invoice_total_subquery = (
            SellInvoice.objects.filter(customer=OuterRef("pk"))
            .values("customer")
            .annotate(total=Coalesce(Sum("grand_total"), Value(Decimal("0.00"))))
            .values("total")[:1]
        )
        payment_total_subquery = (
            PaymentTransaction.objects.filter(customer=OuterRef("pk"))
            .values("customer")
            .annotate(total=Coalesce(Sum("amount"), Value(Decimal("0.00"))))
            .values("total")[:1]
        )
        last_payment_subquery = (
            PaymentTransaction.objects.filter(customer=OuterRef("pk"))
            .order_by("-payment_date")
            .values("payment_date")[:1]
        )

        slow_paying_customers = (
            Customer.objects.annotate(
                total_invoice_amount_calc=Coalesce(
                    Subquery(invoice_total_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                    Value(Decimal("0.00")),
                ),
                total_paid_amount_calc=Coalesce(
                    Subquery(payment_total_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                    Value(Decimal("0.00")),
                ),
                last_payment_date=Subquery(last_payment_subquery),
            )
            .annotate(
                pending_balance_calc=ExpressionWrapper(
                    Coalesce("total_invoice_amount_calc", Value(Decimal("0.00")))
                    - Coalesce("total_paid_amount_calc", Value(Decimal("0.00"))),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
            .filter(pending_balance_calc__gt=0)
            .order_by("last_payment_date", "-pending_balance_calc", "name")[:10]
        )

        totals_all_time = {
            "customers": Customer.objects.count(),
            "invoices": SellInvoice.objects.count(),
            "payments": PaymentTransaction.objects.count(),
        }

        context.update(
            {
                "selected_year": selected_year,
                "available_years": available_years,
                "monthly_chart": monthly_chart,
                "total_sales": total_sales,
                "total_paid": total_paid,
                "total_balance": total_balance,
                "recent_invoices": recent_invoices,
                "slow_paying_customers": slow_paying_customers,
                "totals_all_time": totals_all_time,
                "invoices_this_year_count": yearly_invoices.count(),
            }
        )
        return context

    def get_selected_year(self, available_years, current_year):
        year_param = self.request.GET.get("year")
        try:
            selected_year = int(year_param) if year_param else current_year
        except (TypeError, ValueError):
            selected_year = current_year

        if available_years and selected_year not in available_years:
            return available_years[0]
        return selected_year
