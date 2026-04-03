from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    google_fit_token = models.TextField(blank=True, null=True)
    google_fit_refresh_token = models.TextField(blank=True, null=True)
    burned_calories_manual = models.IntegerField(default=0)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    daily_calorie_goal = models.IntegerField(default=2000)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    target_weight_kg = models.FloatField(null=True, blank=True, verbose_name="Hedef Kilo (kg)")
    
    def __str__(self):
        return f"{self.user.username} - Profil"

    class Meta:
        verbose_name = "Kullanıcı Profili"


class WeightLog(models.Model):
    """Kilo takip kayıtları"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_logs')
    weight_kg = models.FloatField(verbose_name="Kilo (kg)")
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=200, blank=True, verbose_name="Not")
    
    def __str__(self):
        return f"{self.user.username} - {self.weight_kg}kg - {self.date}"
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Kilo Kaydı"
        verbose_name_plural = "Kilo Kayıtları"
        unique_together = ['user', 'date']  # Günde bir kilo kaydı


class Meal(models.Model):
    MEAL_TYPES = [
        ('sabah', '🌅 Sabah Kahvaltısı'),
        ('ogle', '☀️ Öğle Yemeği'),
        ('aksam', '🌙 Akşam Yemeği'),
        ('ara', '🍎 Ara Öğün'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meals')
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES, default='ogle')
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    # Yemek bilgisi
    food_description = models.TextField(blank=True, help_text="Yemek açıklaması")
    total_calories = models.IntegerField(default=0)
    protein_g = models.FloatField(default=0, verbose_name="Protein (g)")
    carbs_g = models.FloatField(default=0, verbose_name="Karbonhidrat (g)")
    fat_g = models.FloatField(default=0, verbose_name="Yağ (g)")

    # AI analiz sonucu
    ai_analysis = models.TextField(blank=True)

    # Fotoğraf
    photo = models.ImageField(upload_to='meals/', null=True, blank=True)

    def save(self, *args, **kwargs):
        # Fotoğraf sıkıştırma
        if self.photo:
            from PIL import Image
            from io import BytesIO
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import sys

            img = Image.open(self.photo)

            # EXIF yönlendirme düzeltmesi
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except:
                pass

            # RGB'ye çevir (PNG için)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Boyutlandır (max 800x800)
            max_size = (800, 800)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Sıkıştır
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)

            # Yeni dosya oluştur
            self.photo = InMemoryUploadedFile(
                output, 'ImageField',
                f"{self.photo.name.split('.')[0]}.jpg",
                'image/jpeg',
                sys.getsizeof(output), None
            )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Fotoğrafı sil
        if self.photo:
            import os
            if os.path.isfile(self.photo.path):
                os.remove(self.photo.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.get_meal_type_display()} - {self.date}"

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Öğün"
        verbose_name_plural = "Öğünler"
# Bu satırları UserProfile modeline ekle - aşağıdaki komutla yapacağız


# ── ANTRENMAN MODELLERİ ──────────────────────────────────────

class WorkoutProgram(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_programs')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Exercise(models.Model):
    CATEGORIES = [
        ('gogus', 'Göğüs'),
        ('sirt', 'Sırt'),
        ('omuz', 'Omuz'),
        ('bacak', 'Bacak'),
        ('kol', 'Kol'),
        ('karin', 'Karın'),
        ('diger', 'Diğer'),
    ]
    program = models.ForeignKey(WorkoutProgram, on_delete=models.CASCADE, related_name='exercises')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='diger')
    target_sets = models.IntegerField(default=3)
    target_reps = models.IntegerField(default=10)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class WorkoutLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_logs')
    program = models.ForeignKey(WorkoutProgram, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.program.name} - {self.date}"


class SetLog(models.Model):
    workout_log = models.ForeignKey(WorkoutLog, on_delete=models.CASCADE, related_name='sets')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='set_logs')
    set_number = models.IntegerField(default=1)
    weight_kg = models.FloatField(default=0)
    reps = models.IntegerField(default=0)

    class Meta:
        ordering = ['set_number']

    def __str__(self):
        return f"{self.exercise.name} Set {self.set_number}: {self.weight_kg}kg x {self.reps}"
