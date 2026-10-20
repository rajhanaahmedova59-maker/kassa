from django.db import models
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    icon = models.CharField(max_length=50, default="fa-box", verbose_name="Иконка (FontAwesome)")
    color = models.CharField(max_length=20, default="#3b82f6", verbose_name="Цвет")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ('dona', 'шт'),
        ('kg', 'кг'),
        ('litr', 'л'),
        ('qadoq', 'упак'),
        ('metr', 'м'),
    ]

    name = models.CharField(max_length=200, verbose_name="Название товара")
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Штрих-код")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="Категория")
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Цена продажи (₸)")
    cost_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Себестоимость (₸)")
    stock = models.IntegerField(default=100, verbose_name="Остаток на складе")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='dona', verbose_name="Единица измерения")
    icon = models.CharField(max_length=50, default="fa-shopping-bag", verbose_name="Иконка")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.price:,.0f} ₸"


class ProductSupply(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='supplies', verbose_name="Товар")
    quantity_added = models.IntegerField(verbose_name="Количество прихода")
    previous_stock = models.IntegerField(default=0, verbose_name="Остаток ДО прихода")
    new_stock = models.IntegerField(default=0, verbose_name="Остаток ПОСЛЕ прихода")
    cost_price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="Закупочная цена (₸)")
    supplier = models.CharField(max_length=200, blank=True, null=True, verbose_name="Поставщик / Заметка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время прихода")

    class Meta:
        verbose_name = "Приход товара"
        verbose_name_plural = "Приходы товаров"
        ordering = ['-created_at']

    def __str__(self):
        return f"Приход #{self.id}: {self.product.name if self.product else '---'} (+{self.quantity_added})"



class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Наличные'),
        ('card', 'Банковская карта'),
        ('click', 'Kaspi / QR'),
    ]

    receipt_number = models.CharField(max_length=50, unique=True, verbose_name="Номер чека")
    subtotal_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Сумма без скидки (₸)")
    discount_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Сумма скидки (₸)")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Скидка (%)")
    total_amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name="Итоговая сумма (₸)")
    paid_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Внесено денег (₸)")
    change_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Сдача (₸)")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash', verbose_name="Способ оплаты")
    cashier_name = models.CharField(max_length=100, default='Кассир 1', verbose_name="Продавец/Кассир")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время продажи")

    class Meta:
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"
        ordering = ['-created_at']

    def __str__(self):
        return f"Чек #{self.receipt_number} - {self.total_amount:,.0f} ₸"

    @classmethod
    def generate_receipt_number(cls):
        import random
        import time
        prefix = time.strftime("%Y%m%d")
        rand = random.randint(1000, 9999)
        return f"CHK-{prefix}-{rand}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items', verbose_name="Продажа")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, verbose_name="Товар")
    product_name = models.CharField(max_length=200, verbose_name="Название товара")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    unit_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Цена за ед.")
    total_price = models.DecimalField(max_digits=14, decimal_places=0, verbose_name="Итоговая цена")

    class Meta:
        verbose_name = "Проданный товар"
        verbose_name_plural = "Проданные товары"

    def __str__(self):
        return f"{self.product_name} x {self.quantity} = {self.total_price:,.0f} ₸"


class Cashier(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Исм (Кассир исми)")
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Ойлик маош (₸)")
    is_active = models.BooleanField(default=True, verbose_name="Фаол")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Кассир"
        verbose_name_plural = "Кассирлар"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def daily_salary(self):
        """Ойлик маошни 26 иш кунига бўлиш"""
        return round(float(self.monthly_salary) / 26, 0)
