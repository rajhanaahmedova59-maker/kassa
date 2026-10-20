from django.core.management.base import BaseCommand
from kassa.models import Category, Product

class Command(BaseCommand):
    help = 'Populates the database with Kazakhstani Tenge prices for Kassa POS'

    def handle(self, *args, **options):
        self.stdout.write("Baza ma'lumotlarini Qozog'iston Tengasida yangilash boshlandi...")

        categories_data = [
            {'name': 'Oziq-ovqat', 'icon': 'fa-bread-slice', 'color': '#f59e0b'},
            {'name': 'Ichimliklar', 'icon': 'fa-bottle-water', 'color': '#06b6d4'},
            {'name': 'Qandolatchilik', 'icon': 'fa-cookie-bite', 'color': '#ec4899'},
            {'name': 'Mevalar va Sabzavotlar', 'icon': 'fa-apple-whole', 'color': '#10b981'},
            {'name': 'Maishiy kimyo', 'icon': 'fa-pump-soap', 'color': '#8b5cf6'},
        ]

        cats = {}
        for c in categories_data:
            cat_obj, created = Category.objects.get_or_create(
                name=c['name'],
                defaults={'icon': c['icon'], 'color': c['color']}
            )
            cats[c['name']] = cat_obj

        products_data = [
            {'name': 'Qolip non', 'barcode': '20000001', 'category': 'Oziq-ovqat', 'price': 180, 'cost_price': 140, 'stock': 150, 'unit': 'dona', 'icon': 'fa-bread-slice'},
            {'name': 'Patir non', 'barcode': '20000002', 'category': 'Oziq-ovqat', 'price': 450, 'cost_price': 350, 'stock': 40, 'unit': 'dona', 'icon': 'fa-cheese'},
            {'name': 'Sut Musaffo 1.5L', 'barcode': '20000003', 'category': 'Oziq-ovqat', 'price': 550, 'cost_price': 420, 'stock': 60, 'unit': 'dona', 'icon': 'fa-box-tissue'},
            {'name': 'Guruch Lazer 1kg', 'barcode': '20000004', 'category': 'Oziq-ovqat', 'price': 850, 'cost_price': 700, 'stock': 100, 'unit': 'kg', 'icon': 'fa-bowl-rice'},
            {'name': 'Pista yog\'i 1L', 'barcode': '20000005', 'category': 'Oziq-ovqat', 'price': 950, 'cost_price': 800, 'stock': 85, 'unit': 'dona', 'icon': 'fa-bottle-droplet'},
            
            {'name': 'Coca-Cola 1.5L', 'barcode': '20000006', 'category': 'Ichimliklar', 'price': 650, 'cost_price': 500, 'stock': 120, 'unit': 'dona', 'icon': 'fa-wine-bottle'},
            {'name': 'Pepsi 1.5L', 'barcode': '20000007', 'category': 'Ichimliklar', 'price': 600, 'cost_price': 480, 'stock': 90, 'unit': 'dona', 'icon': 'fa-wine-bottle'},
            {'name': 'Chortoq gazli suv 0.5L', 'barcode': '20000008', 'category': 'Ichimliklar', 'price': 350, 'cost_price': 250, 'stock': 200, 'unit': 'dona', 'icon': 'fa-bottle-water'},
            {'name': 'Nescafe 3in1 Classic', 'barcode': '20000009', 'category': 'Ichimliklar', 'price': 150, 'cost_price': 100, 'stock': 300, 'unit': 'dona', 'icon': 'fa-mug-hot'},

            {'name': 'Alpen Gold Shokolad', 'barcode': '20000010', 'category': 'Qandolatchilik', 'price': 650, 'cost_price': 500, 'stock': 75, 'unit': 'dona', 'icon': 'fa-cookie'},
            {'name': 'Pechenye ChocoPie', 'barcode': '20000011', 'category': 'Qandolatchilik', 'price': 1400, 'cost_price': 1100, 'stock': 30, 'unit': 'qadoq', 'icon': 'fa-box'},
            
            {'name': 'Qizil Olma Fuji 1kg', 'barcode': '20000012', 'category': 'Mevalar va Sabzavotlar', 'price': 700, 'cost_price': 500, 'stock': 50, 'unit': 'kg', 'icon': 'fa-apple-whole'},
            {'name': 'Banan 1kg', 'barcode': '20000013', 'category': 'Mevalar va Sabzavotlar', 'price': 950, 'cost_price': 750, 'stock': 45, 'unit': 'kg', 'icon': 'fa-lemon'},
            {'name': 'Kartoshka 1kg', 'barcode': '20000014', 'category': 'Mevalar va Sabzavotlar', 'price': 250, 'cost_price': 180, 'stock': 250, 'unit': 'kg', 'icon': 'fa-seedling'},

            {'name': 'Duru Sovun 4x90g', 'barcode': '20000015', 'category': 'Maishiy kimyo', 'price': 850, 'cost_price': 650, 'stock': 40, 'unit': 'qadoq', 'icon': 'fa-pump-soap'},
            {'name': 'Colgate Tish pastasi', 'barcode': '20000016', 'category': 'Maishiy kimyo', 'price': 750, 'cost_price': 550, 'stock': 55, 'unit': 'dona', 'icon': 'fa-tooth'},
        ]

        count = 0
        for p in products_data:
            cat_obj = cats.get(p['category'])
            prod_obj, created = Product.objects.update_or_create(
                barcode=p['barcode'],
                defaults={
                    'name': p['name'],
                    'category': cat_obj,
                    'price': p['price'],
                    'cost_price': p['cost_price'],
                    'stock': p['stock'],
                    'unit': p['unit'],
                    'icon': p['icon']
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Muvaffaqiyatli yakunlandi! {count} ta mahsulot narxlari Tengeda (Tenge) yangilandi."))
