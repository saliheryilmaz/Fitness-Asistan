from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Meal, WeightLog


class KayitForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-posta")
    first_name = forms.CharField(max_length=50, required=False, label="Ad")
    last_name = forms.CharField(max_length=50, required=False, label="Soyad")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'


class ProfilForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['daily_calorie_goal', 'height_cm', 'weight_kg', 'target_weight_kg', 'age', 'gender', 'activity_level']
        labels = {
            'daily_calorie_goal': 'Günlük Kalori Hedefi (kcal)',
            'height_cm': 'Boy (cm)',
            'weight_kg': 'Mevcut Kilo (kg)',
            'target_weight_kg': 'Hedef Kilo (kg)',
            'age': 'Yaş',
            'gender': 'Cinsiyet',
            'activity_level': 'Aktivite Seviyesi',
        }
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-input'}, choices=[('erkek', 'Erkek'), ('kadin', 'Kadın')]),
            'activity_level': forms.Select(attrs={'class': 'form-input'}, choices=[
                ('sedanter', 'Hareketsiz (masa başı iş)'),
                ('hafif', 'Hafif aktif (haftada 1-3 gün)'),
                ('orta', 'Orta aktif (haftada 3-5 gün)'),
                ('aktif', 'Çok aktif (haftada 6-7 gün)'),
                ('cok_aktif', 'Ekstra aktif (günde 2x antrenman)'),
            ]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('gender', 'activity_level'):
                field.widget.attrs['class'] = 'form-input'


class WeightLogForm(forms.ModelForm):
    class Meta:
        model = WeightLog
        fields = ['weight_kg', 'date', 'note']
        labels = {
            'weight_kg': 'Kilo (kg)',
            'date': 'Tarih',
            'note': 'Not (isteğe bağlı)',
        }
        widgets = {
            'weight_kg': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '75.5',
                'step': '0.1'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date'
            }),
            'note': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Örn: Sabah açken tartıldı'
            }),
        }


class OgunForm(forms.ModelForm):
    # Manuel giriş alanları (isteğe bağlı)
    manuel_kalori = forms.IntegerField(
        required=False, 
        label='Kalori (kcal) - Manuel',
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Örn: 450'
        })
    )
    manuel_protein = forms.FloatField(
        required=False,
        label='Protein (g) - Manuel',
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Örn: 25.5'
        })
    )
    manuel_karbonhidrat = forms.FloatField(
        required=False,
        label='Karbonhidrat (g) - Manuel',
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Örn: 45.0'
        })
    )
    manuel_yag = forms.FloatField(
        required=False,
        label='Yağ (g) - Manuel',
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Örn: 12.3'
        })
    )
    
    class Meta:
        model = Meal
        fields = ['date', 'meal_type', 'food_description', 'photo']
        labels = {
            'date': 'Tarih',
            'meal_type': 'Öğün Türü',
            'food_description': 'Ne yedin?',
            'photo': 'Yemek Fotoğrafı (isteğe bağlı)',
        }
        widgets = {
            'date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'food_description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Örn: 1 porsiyon mercimek çorbası, 2 dilim ekmek... (Fotoğraf yüklüyorsan boş bırakabilirsin)',
                'class': 'form-input',
                'required': False,
            }),
            'meal_type': forms.Select(attrs={'class': 'form-input'}),
            'photo': forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        food_description = cleaned_data.get('food_description')
        photo = cleaned_data.get('photo')
        manuel_kalori = cleaned_data.get('manuel_kalori')
        
        # En az birisi dolu olmalı
        if not food_description and not photo and not manuel_kalori:
            raise forms.ValidationError('Lütfen yemek açıklaması girin, fotoğraf yükleyin veya manuel kalori girin.')
        
        return cleaned_data
