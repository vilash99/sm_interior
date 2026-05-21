from django import template

from sales.models import ShopDetail

register = template.Library()


@register.simple_tag
def get_shop_detail():
    return ShopDetail.objects.order_by("-id").first()
