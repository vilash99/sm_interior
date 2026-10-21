from base64 import b64decode
from datetime import date, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree

import qrcode

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Customer, PaymentTransaction, SellInvoice, ShopDetail


@override_settings(SECURE_SSL_REDIRECT=False)
class PaymentTransactionListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = date(2026, 10, 20)
        cls.customer = Customer.objects.create(name="Date Filter Customer")
        cls.invoice = SellInvoice.objects.create(
            customer=cls.customer, invoice_number="FILTER-INVOICE"
        )
        cls.payments = []
        for offset in (-2, -1, 0, 1):
            cls.payments.append(PaymentTransaction.objects.create(
                customer=cls.customer,
                invoice=cls.invoice,
                payment_date=cls.today + timedelta(days=offset),
                amount="100.00",
                payment_mode="upi",
                reference_number="FILTER-REFERENCE",
            ))
        cls.user = get_user_model().objects.create_superuser(username="payment-admin")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("sales:paymenttransaction_list")
        localdate = patch("sales.views.timezone.localdate", return_value=self.today)
        localdate.start()
        self.addCleanup(localdate.stop)

    def test_default_and_reset_show_only_today(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["payments"]), [self.payments[2]])
        self.assertEqual(response.context["search_query"], "")
        for name in ("start_date", "end_date"):
            self.assertEqual(response.context[name], self.today.isoformat())
        self.assertContains(response, f'href="{self.url}"')

    def test_date_range_includes_both_boundaries(self):
        response = self.client.get(self.url, {
            "start_date": "2026-10-18", "end_date": "2026-10-19",
        })
        self.assertEqual(list(response.context["payments"]), self.payments[1::-1])
        self.assertContains(response, 'value="2026-10-18"')
        self.assertContains(response, 'value="2026-10-19"')

    def test_search_fields_are_combined_with_date_range(self):
        for query in ("Date Filter", "FILTER-INVOICE", "FILTER-REFERENCE", "upi"):
            with self.subTest(query=query):
                response = self.client.get(self.url, {
                    "q": query,
                    "start_date": "2026-10-18", "end_date": "2026-10-19",
                })
                self.assertEqual(list(response.context["payments"]), self.payments[1::-1])
        response = self.client.get(self.url, {
            "q": "no matching payment",
            "start_date": "2026-10-18", "end_date": "2026-10-19",
        })
        self.assertEqual(list(response.context["payments"]), [])

    def test_blank_or_invalid_dates_fall_back_to_today(self):
        for value in ("", "invalid", "2026-02-30"):
            with self.subTest(value=value):
                response = self.client.get(self.url, {"start_date": value, "end_date": value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context["payments"]), [self.payments[2]])

    def test_pagination_preserves_search_and_date_range(self):
        PaymentTransaction.objects.bulk_create([
            PaymentTransaction(
                customer=self.customer, payment_date=self.today,
                amount="10.00", payment_mode="upi",
            ) for _ in range(26)
        ])
        filters = {"q": "upi", "start_date": "2026-10-20", "end_date": "2026-10-20"}
        response = self.client.get(self.url, filters)
        self.assertContains(response, "q=upi&amp;start_date=2026-10-20&amp;end_date=2026-10-20&amp;page=2")
        response = self.client.get(self.url, {**filters, "page": 2})
        self.assertEqual(len(response.context["payments"]), 2)
        self.assertTrue(all(payment.payment_date == self.today for payment in response.context["payments"]))


@override_settings(SECURE_SSL_REDIRECT=False)
class InvoicePaymentQRCodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Customer.objects.create(name="Invoice Customer")
        cls.invoice = SellInvoice.objects.create(
            customer=cls.customer, invoice_number="INV/123 & 4", grand_total="1234.50",
        )
        cls.shop = ShopDetail.objects.create(
            shop_name="Interiors & More", full_address="Shop address",
            upi_id="sample@upi", show_upi=True,
        )
        cls.user = get_user_model().objects.create_superuser(username="invoice-admin")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("sales:sell_invoice_preview", kwargs={"pk": self.invoice.pk})

    def test_qr_encodes_payee_invoice_and_full_amount(self):
        PaymentTransaction.objects.create(
            customer=self.customer, invoice=self.invoice, amount="100.00", payment_mode="cash",
        )
        with patch("sales.views.qrcode.make", wraps=qrcode.make) as make_qr:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        uri = urlsplit(make_qr.call_args.args[0])
        self.assertEqual((uri.scheme, uri.netloc), ("upi", "pay"))
        self.assertEqual(parse_qs(uri.query), {
            "pa": ["sample@upi"], "pn": ["Interiors & More"],
            "tr": ["INV/123 & 4"],
            "am": ["1234.50"], "cu": ["INR"],
        })
        qr_data = response.context["upi_qr_code"]
        self.assertTrue(qr_data.startswith("data:image/svg+xml;base64,"))
        svg = ElementTree.fromstring(b64decode(qr_data.split(",", 1)[1]))
        self.assertEqual(svg.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertContains(response, '<td class="payment-qr">')
        self.assertContains(response, 'src="' + qr_data + '"')

    @override_settings(UPI_ID="ignored-env-value@upi")
    def test_no_qr_when_upi_id_is_not_configured(self):
        self.shop.upi_id = ""
        self.shop.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<td class="payment-qr">')
        self.assertContains(response, "Interiors &amp; More")

    def test_disabling_upi_hides_qr_and_skips_generation(self):
        self.shop.show_upi = False
        self.shop.save()
        with patch("sales.views.qrcode.make") as make_qr:
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        make_qr.assert_not_called()
        self.assertNotContains(response, '<td class="payment-qr">')
        self.assertNotIn("upi_qr_code", response.context)

    def test_no_payment_qr_for_zero_amount(self):
        self.invoice.grand_total = 0
        self.invoice.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<td class="payment-qr">')

    def test_invoice_without_shop_details_still_renders(self):
        self.shop.delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<td class="payment-qr">')
        self.assertContains(response, "Shop Name")
