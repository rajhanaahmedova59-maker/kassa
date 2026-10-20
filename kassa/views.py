import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Category, Product, ProductSupply, Sale, SaleItem, Cashier


def pos_terminal_view(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).select_related('category')
    
    # Filter by category if query parameter present
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
        
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(barcode__icontains=search_query)
        )

    # Active cashiers for dropdown selector
    cashiers = Cashier.objects.filter(is_active=True).order_by('name')
    # Current cashier from session or first available
    current_cashier_name = request.session.get('current_cashier', '')
    if not current_cashier_name and cashiers.exists():
        current_cashier_name = cashiers.first().name
        request.session['current_cashier'] = current_cashier_name

    context = {
        'categories': categories,
        'products': products,
        'selected_category': category_id,
        'search_query': search_query,
        'cashiers': cashiers,
        'current_cashier_name': current_cashier_name,
    }
    return render(request, 'kassa/pos.html', context)


@csrf_exempt
def set_cashier_api(request):
    """Session'da joriy kassirni saqlash"""
    if request.method == 'POST':
        data = json.loads(request.body)
        cashier_name = data.get('cashier_name', '').strip()
        if cashier_name:
            request.session['current_cashier'] = cashier_name
            return JsonResponse({'success': True, 'cashier_name': cashier_name})
        return JsonResponse({'success': False, 'error': 'Kassir nomi bo\'sh'}, status=400)
    return JsonResponse({'success': False, 'error': 'Faqat POST'}, status=405)


@csrf_exempt
def create_sale_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Принимаются только POST-запросы'}, status=405)

    try:
        data = json.loads(request.body)
        cart_items = data.get('items', [])
        payment_method = data.get('payment_method', 'cash')
        paid_amount = float(data.get('paid_amount', 0))
        discount_percent = float(data.get('discount_percent', 0))
        custom_discount_amount = float(data.get('discount_amount', 0))

        if not cart_items:
            return JsonResponse({'success': False, 'error': 'Корзина пуста!'}, status=400)

        subtotal_amount = 0
        sale_items_data = []

        # Validate products and calculate subtotal
        for item in cart_items:
            product_id = item.get('id')
            qty = int(item.get('quantity', 1))

            if qty <= 0:
                continue

            product = Product.objects.get(id=product_id)
            item_total = float(product.price) * qty
            subtotal_amount += item_total

            sale_items_data.append({
                'product': product,
                'quantity': qty,
                'unit_price': product.price,
                'total_price': item_total
            })

        if subtotal_amount == 0:
            return JsonResponse({'success': False, 'error': 'В корзине нет действующих товаров'}, status=400)

        # Calculate discount
        if discount_percent > 0:
            discount_amount = round(subtotal_amount * (discount_percent / 100.0))
        elif custom_discount_amount > 0:
            discount_amount = custom_discount_amount
        else:
            discount_amount = 0

        discount_amount = max(0, min(discount_amount, subtotal_amount))
        total_amount = subtotal_amount - discount_amount

        # Handle change calculation
        if payment_method == 'cash':
            if paid_amount < total_amount:
                paid_amount = total_amount
            change_amount = paid_amount - total_amount
        else:
            paid_amount = total_amount
            change_amount = 0

        # Create Sale
        sale = Sale.objects.create(
            receipt_number=Sale.generate_receipt_number(),
            subtotal_amount=subtotal_amount,
            discount_amount=discount_amount,
            discount_percent=discount_percent if discount_percent > 0 else (round((discount_amount / subtotal_amount) * 100, 2) if subtotal_amount > 0 else 0),
            total_amount=total_amount,
            paid_amount=paid_amount,
            change_amount=change_amount,
            payment_method=payment_method,
            cashier_name='Кассир 1'
        )

        # Create Sale Items & Reduce Stock
        for item in sale_items_data:
            SaleItem.objects.create(
                sale=sale,
                product=item['product'],
                product_name=item['product'].name,
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['total_price']
            )
            # Reduce product stock
            product = item['product']
            product.stock = max(0, product.stock - item['quantity'])
            product.save()

        return JsonResponse({
            'success': True,
            'receipt_number': sale.receipt_number,
            'sale_id': sale.id,
            'subtotal_amount': sale.subtotal_amount,
            'discount_amount': sale.discount_amount,
            'discount_percent': sale.discount_percent,
            'total_amount': sale.total_amount,
            'paid_amount': sale.paid_amount,
            'change_amount': sale.change_amount,
            'created_at': sale.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def products_list_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_supply':
            product_id = request.POST.get('product_id')
            quantity_added = int(request.POST.get('quantity_added') or 0)
            cost_price = request.POST.get('cost_price') or None
            supplier = request.POST.get('supplier') or ''

            if product_id and quantity_added > 0:
                product = get_object_or_404(Product, id=product_id)
                previous_stock = product.stock
                new_stock = previous_stock + quantity_added
                product.stock = new_stock
                if cost_price and float(cost_price) > 0:
                    product.cost_price = cost_price
                product.save()

                ProductSupply.objects.create(
                    product=product,
                    quantity_added=quantity_added,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    cost_price=cost_price if cost_price else product.cost_price,
                    supplier=supplier
                )
            return redirect('products_list')

        name = request.POST.get('name')
        barcode = request.POST.get('barcode') or None
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        cost_price = request.POST.get('cost_price') or 0
        stock = int(request.POST.get('stock') or 0)
        unit = request.POST.get('unit') or 'dona'

        category = Category.objects.get(id=category_id) if category_id else None

        product = Product.objects.create(
            name=name,
            barcode=barcode,
            category=category,
            price=price,
            cost_price=cost_price,
            stock=stock,
            unit=unit
        )
        if stock > 0:
            ProductSupply.objects.create(
                product=product,
                quantity_added=stock,
                previous_stock=0,
                new_stock=stock,
                cost_price=cost_price,
                supplier="Начальный приход при создании"
            )
        return redirect('products_list')

    categories = Category.objects.all()
    products = Product.objects.select_related('category').all()
    supplies = ProductSupply.objects.select_related('product', 'product__category').all()[:100]

    total_stock_count = sum(p.stock for p in products)
    total_products_count = products.count()
    total_supplies_count = ProductSupply.objects.count()

    context = {
        'categories': categories,
        'products': products,
        'supplies': supplies,
        'total_stock_count': total_stock_count,
        'total_products_count': total_products_count,
        'total_supplies_count': total_supplies_count,
    }
    return render(request, 'kassa/products.html', context)



def sales_history_view(request):
    sales = Sale.objects.prefetch_related('items').all()
    
    today = timezone.now().date()
    today_sales = sales.filter(created_at__date=today)
    
    today_total = today_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    today_discount = today_sales.aggregate(Sum('discount_amount'))['discount_amount__sum'] or 0
    today_count = today_sales.count()
    
    cash_total = today_sales.filter(payment_method='cash').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    card_total = today_sales.filter(payment_method='card').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    click_total = today_sales.filter(payment_method='click').aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    context = {
        'sales': sales[:50],  # Recent 50 sales
        'today_total': today_total,
        'today_discount': today_discount,
        'today_count': today_count,
        'cash_total': cash_total,
        'card_total': card_total,
        'click_total': click_total,
    }
    return render(request, 'kassa/sales_history.html', context)


def receipt_view(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    return render(request, 'kassa/receipt.html', {'sale': sale})


def report_view(request):
    import json
    from datetime import datetime, time, timedelta, date as dt_date
    from django.db.models import Sum, Count, Max, Min
    from django.utils import timezone

    today = timezone.localdate()
    period = request.GET.get('period', 'today')

    # Determine date range based on period
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif period == 'week':
        start_date = today - timedelta(days=6)
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'last30':
        start_date = today - timedelta(days=29)
        end_date = today
    elif period == 'custom':
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        try:
            start_date = dt_date.fromisoformat(start_date_str) if start_date_str else today
            end_date = dt_date.fromisoformat(end_date_str) if end_date_str else today
        except (ValueError, TypeError):
            start_date = today
            end_date = today
    else:
        start_date = today
        end_date = today

    # Prepare timezone-aware datetime bounds
    current_tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), current_tz)
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max), current_tz)

    # Sales query
    sales = Sale.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt).order_by('-created_at')

    # Aggregates
    sales_agg = sales.aggregate(
        rev_sum=Sum('total_amount'),
        sub_sum=Sum('subtotal_amount'),
        disc_sum=Sum('discount_amount'),
        cnt=Count('id'),
        max_sale=Max('total_amount'),
        min_sale=Min('total_amount')
    )

    total_revenue = float(sales_agg['rev_sum'] or 0)
    total_subtotal = float(sales_agg['sub_sum'] or 0)
    total_discount = float(sales_agg['disc_sum'] or 0)
    total_sales_count = sales_agg['cnt'] or 0
    max_receipt = float(sales_agg['max_sale'] or 0)
    min_receipt = float(sales_agg['min_sale'] or 0) if total_sales_count > 0 else 0
    avg_receipt = (total_revenue / total_sales_count) if total_sales_count > 0 else 0

    # Sales items with related product & category
    sale_items = list(SaleItem.objects.filter(sale__in=sales).select_related('product', 'product__category', 'sale'))

    total_cost = 0.0
    total_units_sold = 0
    discount_sales_count = sum(1 for s in sales if s.discount_amount > 0)
    discount_rate = (discount_sales_count / total_sales_count * 100) if total_sales_count > 0 else 0

    # Map product & category performance
    prod_perf = {}
    cat_perf = {}

    for item in sale_items:
        qty = item.quantity
        rev = float(item.total_price)
        unit_cost = float(item.product.cost_price or 0) if item.product else 0.0
        item_cost = unit_cost * qty
        profit = rev - item_cost

        total_cost += item_cost
        total_units_sold += qty

        # Product grouping
        p_name = item.product_name
        cat_name = item.product.category.name if (item.product and item.product.category) else "Без категории"

        if p_name not in prod_perf:
            prod_perf[p_name] = {
                'product_name': p_name,
                'category_name': cat_name,
                'total_qty': 0,
                'total_revenue': 0.0,
                'total_cost': 0.0,
                'total_profit': 0.0,
                'stock': item.product.stock if item.product else 0,
                'unit': item.product.get_unit_display() if (item.product and hasattr(item.product, 'get_unit_display')) else 'шт',
            }
        prod_perf[p_name]['total_qty'] += qty
        prod_perf[p_name]['total_revenue'] += rev
        prod_perf[p_name]['total_cost'] += item_cost
        prod_perf[p_name]['total_profit'] += profit

        # Category grouping
        if cat_name not in cat_perf:
            cat_perf[cat_name] = {
                'name': cat_name,
                'color': item.product.category.color if (item.product and item.product.category) else '#3b82f6',
                'total_qty': 0,
                'total_revenue': 0.0,
                'total_profit': 0.0,
            }
        cat_perf[cat_name]['total_qty'] += qty
        cat_perf[cat_name]['total_revenue'] += rev
        cat_perf[cat_name]['total_profit'] += profit

    total_profit = total_revenue - total_cost
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    avg_items_per_receipt = (total_units_sold / total_sales_count) if total_sales_count > 0 else 0

    # ABC Analysis on sold products
    sorted_products = sorted(prod_perf.values(), key=lambda x: x['total_revenue'], reverse=True)
    cum_rev = 0.0
    for p in sorted_products:
        p_rev = p['total_revenue']
        cum_rev += p_rev
        cum_pct = (cum_rev / total_revenue * 100) if total_revenue > 0 else 100
        p['share_pct'] = (p_rev / total_revenue * 100) if total_revenue > 0 else 0
        p['margin_pct'] = (p['total_profit'] / p_rev * 100) if p_rev > 0 else 0

        if cum_pct <= 80:
            p['abc_group'] = 'A'
            p['abc_class'] = 'abc-a'
            p['abc_desc'] = 'Локомотив — основная выручка (Топ 80%)'
        elif cum_pct <= 95:
            p['abc_group'] = 'B'
            p['abc_class'] = 'abc-b'
            p['abc_desc'] = 'Стабильный спрос (следующие 15%)'
        else:
            p['abc_group'] = 'C'
            p['abc_class'] = 'abc-c'
            p['abc_desc'] = 'Низкий оборот (последние 5%)'

    abc_counts = {
        'A': sum(1 for p in sorted_products if p['abc_group'] == 'A'),
        'B': sum(1 for p in sorted_products if p['abc_group'] == 'B'),
        'C': sum(1 for p in sorted_products if p['abc_group'] == 'C'),
    }

    # Top products by profit
    top_profit_products = sorted(sorted_products, key=lambda x: x['total_profit'], reverse=True)[:10]

    # Payment Breakdown
    cash_total = float(sales.filter(payment_method='cash').aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
    card_total = float(sales.filter(payment_method='card').aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
    click_total = float(sales.filter(payment_method='click').aggregate(Sum('total_amount'))['total_amount__sum'] or 0)

    cash_count = sales.filter(payment_method='cash').count()
    card_count = sales.filter(payment_method='card').count()
    click_count = sales.filter(payment_method='click').count()

    # Category stats list
    category_stats = sorted(cat_perf.values(), key=lambda x: x['total_revenue'], reverse=True)
    for c in category_stats:
        c['share_pct'] = (c['total_revenue'] / total_revenue * 100) if total_revenue > 0 else 0
        c['margin_pct'] = (c['total_profit'] / c['total_revenue'] * 100) if c['total_revenue'] > 0 else 0

    # Hourly Distribution & Peak Hours Analysis
    hourly_data = {h: {'hour': h, 'label': f"{h:02d}:00", 'revenue': 0.0, 'count': 0} for h in range(24)}
    dayparts = {
        'morning': {'label': 'Утро (06:00 - 12:00)', 'revenue': 0.0, 'count': 0, 'icon': 'fa-sun', 'color': '#f59e0b', 'share_pct': 0},
        'afternoon': {'label': 'День (12:00 - 17:00)', 'revenue': 0.0, 'count': 0, 'icon': 'fa-cloud-sun', 'color': '#06b6d4', 'share_pct': 0},
        'evening': {'label': 'Вечер (17:00 - 22:00)', 'revenue': 0.0, 'count': 0, 'icon': 'fa-moon', 'color': '#8b5cf6', 'share_pct': 0},
        'night': {'label': 'Ночь (22:00 - 06:00)', 'revenue': 0.0, 'count': 0, 'icon': 'fa-star-and-crescent', 'color': '#64748b', 'share_pct': 0},
    }

    for s in sales:
        local_time = timezone.localtime(s.created_at)
        h = local_time.hour
        amt = float(s.total_amount)
        hourly_data[h]['revenue'] += amt
        hourly_data[h]['count'] += 1

        if 6 <= h < 12:
            dayparts['morning']['revenue'] += amt
            dayparts['morning']['count'] += 1
        elif 12 <= h < 17:
            dayparts['afternoon']['revenue'] += amt
            dayparts['afternoon']['count'] += 1
        elif 17 <= h < 22:
            dayparts['evening']['revenue'] += amt
            dayparts['evening']['count'] += 1
        else:
            dayparts['night']['revenue'] += amt
            dayparts['night']['count'] += 1

    for dp in dayparts.values():
        dp['share_pct'] = (dp['revenue'] / total_revenue * 100) if total_revenue > 0 else 0

    # Find peak hour
    peak_candidates = [h for h in hourly_data.values() if h['revenue'] > 0]
    if peak_candidates:
        peak_hour_entry = max(peak_candidates, key=lambda x: x['revenue'])
        peak_hour_label = f"{peak_hour_entry['hour']:02d}:00 - {peak_hour_entry['hour']+1:02d}:00"
        peak_hour_revenue = peak_hour_entry['revenue']
        peak_hour_count = peak_hour_entry['count']
    else:
        peak_hour_label = "—"
        peak_hour_revenue = 0
        peak_hour_count = 0

    # Trend Timeline
    trend_labels = []
    trend_revenues = []
    trend_profits = []
    trend_counts = []

    day_span = (end_date - start_date).days
    day_names_uz = {0: 'Пн', 1: 'Вт', 2: 'Ср', 3: 'Чт', 4: 'Пт', 5: 'Сб', 6: 'Вс'}

    if day_span == 0:
        for h in range(8, 24):
            trend_labels.append(f"{h:02d}:00")
            h_rev = hourly_data[h]['revenue']
            trend_revenues.append(round(h_rev, 0))
            trend_counts.append(hourly_data[h]['count'])
            trend_profits.append(round(h_rev * (profit_margin / 100.0) if total_revenue > 0 else 0, 0))
    else:
        for i in range(day_span + 1):
            curr_d = start_date + timedelta(days=i)
            d_sales = [s for s in sales if timezone.localtime(s.created_at).date() == curr_d]
            d_rev = sum(float(s.total_amount) for s in d_sales)
            d_cnt = len(d_sales)
            d_profit = d_rev * (profit_margin / 100.0) if total_revenue > 0 else 0
            trend_labels.append(f"{curr_d.strftime('%d.%m')} ({day_names_uz.get(curr_d.weekday(), '')})")
            trend_revenues.append(round(d_rev, 0))
            trend_profits.append(round(d_profit, 0))
            trend_counts.append(d_cnt)

    # Inventory Analysis
    all_active_products = list(Product.objects.filter(is_active=True).select_related('category'))
    total_stock_count = sum(p.stock for p in all_active_products)  # Общий остаток в штуках
    total_stock_value_cost = sum(p.stock * float(p.cost_price or 0) for p in all_active_products)
    total_stock_value_price = sum(p.stock * float(p.price) for p in all_active_products)
    potential_stock_profit = total_stock_value_price - total_stock_value_cost

    low_stock_products = [p for p in all_active_products if p.stock <= 10]
    low_stock_products = sorted(low_stock_products, key=lambda p: p.stock)[:12]

    sold_product_names = set(prod_perf.keys())
    zero_sale_products = [p for p in all_active_products if p.name not in sold_product_names and p.stock > 0]
    zero_sale_tied_capital = sum(p.stock * float(p.cost_price or 0) for p in zero_sale_products)

    # Топ-10 по количеству продаж (единиц)
    top_by_qty = sorted(sorted_products, key=lambda x: x['total_qty'], reverse=True)[:10]

    # Запасы по категориям для диаграммы
    stock_by_category = {}
    for p in all_active_products:
        cat_name = p.category.name if p.category else 'Без категории'
        cat_color = p.category.color if p.category else '#94a3b8'
        if cat_name not in stock_by_category:
            stock_by_category[cat_name] = {'name': cat_name, 'color': cat_color, 'stock': 0, 'count': 0}
        stock_by_category[cat_name]['stock'] += p.stock
        stock_by_category[cat_name]['count'] += 1
    stock_by_category_list = sorted(stock_by_category.values(), key=lambda x: x['stock'], reverse=True)

    # Chart datasets JSON for frontend Chart.js
    chart_data = {
        'trend': {
            'labels': trend_labels,
            'revenues': trend_revenues,
            'profits': trend_profits,
            'counts': trend_counts,
            'is_hourly': (day_span == 0)
        },
        'payment': {
            'labels': ['Наличные', 'Банковская карта', 'Kaspi / QR'],
            'data': [cash_total, card_total, click_total],
            'colors': ['#f59e0b', '#3b82f6', '#8b5cf6'],
        },
        'top_qty': {
            'labels': [p['product_name'][:20] for p in top_by_qty],
            'data': [p['total_qty'] for p in top_by_qty],
            'colors': ['#059669', '#10b981', '#34d399', '#6ee7b7', '#a7f3d0',
                       '#2563eb', '#3b82f6', '#60a5fa', '#8b5cf6', '#a78bfa'],
        },
        'stock_category': {
            'labels': [c['name'] for c in stock_by_category_list[:8]],
            'data': [c['stock'] for c in stock_by_category_list[:8]],
            'colors': [c['color'] for c in stock_by_category_list[:8]],
        },
        'categories': {
            'labels': [c['name'] for c in category_stats[:8]],
            'revenues': [round(c['total_revenue'], 0) for c in category_stats[:8]],
            'colors': [c['color'] for c in category_stats[:8]],
        },
        'hourly': {
            'labels': [f"{h:02d}:00" for h in range(8, 23)],
            'data': [round(hourly_data[h]['revenue'], 0) for h in range(8, 23)],
            'counts': [hourly_data[h]['count'] for h in range(8, 23)],
        }
    }

    context = {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_subtotal': total_subtotal,
        'total_discount': total_discount,
        'total_sales_count': total_sales_count,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'avg_receipt': avg_receipt,
        'max_receipt': max_receipt,
        'min_receipt': min_receipt,
        'total_units_sold': total_units_sold,
        'avg_items_per_receipt': avg_items_per_receipt,
        'discount_rate': discount_rate,
        'cash_total': cash_total,
        'card_total': card_total,
        'click_total': click_total,
        'cash_count': cash_count,
        'card_count': card_count,
        'click_count': click_count,
        'sorted_products': sorted_products,
        'top_products': sorted_products[:10],
        'top_profit_products': top_profit_products,
        'abc_counts': abc_counts,
        'category_stats': category_stats,
        'dayparts': dayparts,
        'peak_hour_label': peak_hour_label,
        'peak_hour_revenue': peak_hour_revenue,
        'peak_hour_count': peak_hour_count,
        'total_products': len(all_active_products),
        'total_stock_count': total_stock_count,
        'total_stock_value_cost': total_stock_value_cost,
        'total_stock_value_price': total_stock_value_price,
        'potential_stock_profit': potential_stock_profit,
        'low_stock_products': low_stock_products,
        'zero_sale_products': zero_sale_products[:12],
        'zero_sale_count': len(zero_sale_products),
        'zero_sale_tied_capital': zero_sale_tied_capital,
        'top_by_qty': top_by_qty,
        'stock_by_category_list': stock_by_category_list,
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'kassa/report.html', context)



def cashier_view(request):
    """Kassirlar ro'yxati - oylik va kunlik maosh bilan"""
    from datetime import datetime, time, timedelta
    from django.db.models import Sum, Count
    from django.utils import timezone

    # Handle form submissions
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_cashier':
            name = request.POST.get('name', '').strip()
            monthly_salary = request.POST.get('monthly_salary', 0)
            if name:
                Cashier.objects.get_or_create(
                    name=name,
                    defaults={'monthly_salary': monthly_salary}
                )
            return redirect('cashier_list')

        elif action == 'edit_cashier':
            cashier_id = request.POST.get('cashier_id')
            name = request.POST.get('name', '').strip()
            monthly_salary = request.POST.get('monthly_salary', 0)
            try:
                cashier = Cashier.objects.get(id=cashier_id)
                cashier.name = name
                cashier.monthly_salary = monthly_salary
                cashier.save()
            except Cashier.DoesNotExist:
                pass
            return redirect('cashier_list')

        elif action == 'delete_cashier':
            cashier_id = request.POST.get('cashier_id')
            Cashier.objects.filter(id=cashier_id).delete()
            return redirect('cashier_list')

    today = timezone.localdate()
    current_tz = timezone.get_current_timezone()
    today_start = timezone.make_aware(datetime.combine(today, time.min), current_tz)
    today_end = timezone.make_aware(datetime.combine(today, time.max), current_tz)

    month_start = today.replace(day=1)
    month_start_dt = timezone.make_aware(datetime.combine(month_start, time.min), current_tz)

    # Get all cashiers
    cashiers = Cashier.objects.filter(is_active=True)

    cashier_stats = []
    total_monthly_salary_fund = 0

    # Get all sale cashier names from DB
    all_sale_cashier_names = Sale.objects.values_list('cashier_name', flat=True).distinct()

    for cashier in cashiers:
        # Today's sales by this cashier
        today_sales = Sale.objects.filter(
            cashier_name=cashier.name,
            created_at__gte=today_start,
            created_at__lte=today_end
        )
        today_revenue = float(today_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
        today_count = today_sales.count()

        # This month's sales
        month_sales = Sale.objects.filter(
            cashier_name=cashier.name,
            created_at__gte=month_start_dt
        )
        month_revenue = float(month_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
        month_count = month_sales.count()

        # Total all-time sales
        all_sales = Sale.objects.filter(cashier_name=cashier.name)
        total_revenue = float(all_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
        total_count = all_sales.count()

        daily_salary = cashier.daily_salary
        monthly_salary = float(cashier.monthly_salary)
        total_monthly_salary_fund += monthly_salary

        cashier_stats.append({
            'cashier': cashier,
            'today_revenue': today_revenue,
            'today_count': today_count,
            'month_revenue': month_revenue,
            'month_count': month_count,
            'total_revenue': total_revenue,
            'total_count': total_count,
            'daily_salary': daily_salary,
            'monthly_salary': monthly_salary,
        })

    # Sort by monthly_salary descending
    cashier_stats.sort(key=lambda x: x['monthly_salary'], reverse=True)

    # Also show cashier names from sales that are NOT in Cashier model
    registered_names = set(c.name for c in cashiers)
    unregistered_cashiers = [
        name for name in all_sale_cashier_names if name not in registered_names
    ]

    context = {
        'cashier_stats': cashier_stats,
        'total_monthly_salary_fund': total_monthly_salary_fund,
        'total_daily_fund': round(total_monthly_salary_fund / 26, 0) if total_monthly_salary_fund > 0 else 0,
        'cashier_count': cashiers.count(),
        'today': today,
        'month_start': month_start,
        'unregistered_cashiers': unregistered_cashiers,
    }
    return render(request, 'kassa/cashiers.html', context)
