from django.urls import path
from . import views

urlpatterns = [
    path('', views.pos_terminal_view, name='pos_terminal'),
    path('api/sale/create/', views.create_sale_api, name='create_sale_api'),
    path('api/set-cashier/', views.set_cashier_api, name='set_cashier_api'),
    path('products/', views.products_list_view, name='products_list'),
    path('sales/', views.sales_history_view, name='sales_history'),
    path('receipt/<int:sale_id>/', views.receipt_view, name='receipt_view'),
    path('report/', views.report_view, name='report'),
    path('cashiers/', views.cashier_view, name='cashier_list'),
]
