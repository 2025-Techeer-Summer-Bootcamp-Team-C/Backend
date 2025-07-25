# order/models.py
from django.db import models
from django.conf import settings
from product.models import Product

User = settings.AUTH_USER_MODEL

class Order(models.Model):
    STATUS_ORDERED = 'ORDERED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_ORDERED, 'Ordered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ORDERED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} by {self.user}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = [('order', 'product')]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def price_per_item(self):
        return self.product.price

    @property
    def total_price(self):
        return self.quantity * self.product.price