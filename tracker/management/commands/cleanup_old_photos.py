"""
Eski fotoğrafları temizleme komutu
Kullanım: python manage.py cleanup_old_photos
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tracker.models import Meal
import os


class Command(BaseCommand):
    help = '30 günden eski öğün fotoğraflarını siler'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Kaç günden eski fotoğraflar silinsin (varsayılan: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece göster, silme (test modu)'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # X günden eski kayıtlar
        cutoff_date = timezone.now() - timedelta(days=days)
        old_meals = Meal.objects.filter(
            created_at__lt=cutoff_date,
            photo__isnull=False
        ).exclude(photo='')
        
        count = old_meals.count()
        total_size = 0
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {days} günden eski fotoğraf bulunamadı.')
            )
            return
        
        self.stdout.write(f'📸 {count} adet eski fotoğraf bulundu...')
        
        for meal in old_meals:
            if meal.photo and os.path.isfile(meal.photo.path):
                file_size = os.path.getsize(meal.photo.path)
                total_size += file_size
                
                if dry_run:
                    self.stdout.write(
                        f'  - {meal.photo.name} ({file_size / 1024:.1f} KB) - {meal.date}'
                    )
                else:
                    try:
                        os.remove(meal.photo.path)
                        meal.photo = None
                        meal.save()
                        self.stdout.write(
                            self.style.WARNING(f'  ❌ Silindi: {meal.photo.name}')
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ⚠️ Hata: {meal.photo.name} - {e}')
                        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 TEST MODU: {count} fotoğraf silinecek '
                    f'(toplam {total_size / 1024 / 1024:.2f} MB)'
                )
            )
            self.stdout.write('Gerçekten silmek için --dry-run olmadan çalıştır')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ {count} fotoğraf silindi! '
                    f'{total_size / 1024 / 1024:.2f} MB alan kazanıldı.'
                )
            )
