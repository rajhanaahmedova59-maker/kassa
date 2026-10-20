from django.contrib import admin
from .models import Category, Product, ProductSupply, Sale, SaleItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color', 'created_at')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'barcode', 'category', 'price', 'cost_price', 'stock', 'unit', 'is_active')
    list_filter = ('category', 'is_active', 'unit')
    search_fields = ('name', 'barcode')
    list_editable = ('price', 'stock', 'is_active')

@admin.register(ProductSupply)
class ProductSupplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity_added', 'previous_stock', 'new_stock', 'cost_price', 'supplier', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('product__name', 'supplier')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('product_name', 'quantity', 'unit_price', 'total_price')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'total_amount', 'paid_amount', 'change_amount', 'payment_method', 'cashier_name', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('receipt_number', 'cashier_name')
    inlines = [SaleItemInline]
