import os
import base64
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from datetime import date, timedelta
from .models import UserProfile, Meal, WeightLog
from .forms import KayitForm, ProfilForm, OgunForm, WeightLogForm
from django.conf import settings
from PIL import Image
import io


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def analyze_with_claude(food_text=None, image_data=None, image_type=None):
    from django.conf import settings
    from groq import Groq

    groq_key = getattr(settings, 'GROQ_API_KEY', '').strip()
    if not groq_key or len(groq_key) < 20:
        return {
            "toplam_kalori": 0, "protein_g": 0, "karbonhidrat_g": 0, "yag_g": 0,
            "yemekler": [],
            "aciklama": "GROQ_API_KEY tanimlanmadi."
        }

    prompt = """Sen bir beslenme uzmanisin. Kullanicinin yedigi yemekleri analiz edip kalori ve besin degerlerini hesapliyorsun. Her zaman Turkce yanit ver.

Yanitini SADECE su JSON formatinda ver, baska hicbir sey yazma:
{
    "toplam_kalori": 450,
    "protein_g": 25.5,
    "karbonhidrat_g": 45.0,
    "yag_g": 12.3,
    "yemekler": [
        {"isim": "Mercimek corbasi", "miktar": "1 porsiyon", "kalori": 200}
    ],
    "aciklama": "Bu ogun dengeli bir ogundur."
}"""

    try:
        client = Groq(api_key=groq_key)

        if image_data:
            user_content = [
                {"type": "image_url", "image_url": {"url": f"data:{image_type};base64,{image_data}"}},
                {"type": "text", "text": prompt + "\n\nBu yemek fotografini analiz et."}
            ]
            model = "meta-llama/llama-4-scout-17b-16e-instruct"
        else:
            user_content = prompt + f"\n\nSu yemekleri analiz et: {food_text}"
            model = "llama-3.3-70b-versatile"

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_content}],
            max_tokens=1000,
        )

        response_text = response.choices[0].message.content.strip()

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        return json.loads(response_text)

    except Exception as e:
        import traceback
        print(f"Groq API Hatasi: {traceback.format_exc()}")
        return {
            "toplam_kalori": 0, "protein_g": 0, "karbonhidrat_g": 0, "yag_g": 0,
            "yemekler": [],
            "aciklama": f"API hatasi: {str(e)[:200]}"
        }

def giris(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    else:
        form = AuthenticationForm()

    return render(request, 'tracker/giris.html', {'form': form})


def kayit(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = KayitForm(request.POST)
        if form.is_valid():
            user = form.save()
            get_or_create_profile(user)
            login(request, user)
            messages.success(request, f'Hoş geldin, {user.username}! 🎉')
            return redirect('profil_duzenle')
    else:
        form = KayitForm()

    return render(request, 'tracker/kayit.html', {'form': form})


def cikis(request):
    logout(request)
    return redirect('giris')


# ── MAIN VIEWS ──────────────────────────────────────────────

@login_required
def dashboard(request):
    profile = get_or_create_profile(request.user)
    today = date.today()

    today_meals = Meal.objects.filter(user=request.user, date=today)

    totals = today_meals.aggregate(
        total_cal=Sum('total_calories'),
        total_protein=Sum('protein_g'),
        total_carbs=Sum('carbs_g'),
        total_fat=Sum('fat_g'),
    )

    total_cal = totals['total_cal'] or 0
    goal = profile.daily_calorie_goal
    progress_pct = min(int((total_cal / goal) * 100), 100) if goal > 0 else 0
    remaining = max(goal - total_cal, 0)

    circumference = 282.7
    ring_offset = circumference - (circumference * progress_pct / 100)

    meals_by_type = {}
    for meal_type, label in Meal.MEAL_TYPES:
        type_meals = today_meals.filter(meal_type=meal_type)
        type_cal = type_meals.aggregate(Sum('total_calories'))['total_calories__sum'] or 0
        meals_by_type[meal_type] = {
            'label': label,
            'calories': type_cal,
            'meals': type_meals,
        }

    week_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_cal = Meal.objects.filter(user=request.user, date=d).aggregate(
            Sum('total_calories'))['total_calories__sum'] or 0
        week_data.append({'date': d.strftime('%a'), 'calories': day_cal, 'goal': goal})

    weight_logs = WeightLog.objects.filter(
        user=request.user,
        date__gte=today - timedelta(days=30)
    ).order_by('date')

    weight_data = []
    for log in weight_logs:
        weight_data.append({
            'date': log.date.strftime('%d/%m'),
            'weight': float(log.weight_kg)
        })

    latest_weight = weight_logs.last()
    first_weight = weight_logs.first()
    weight_change = None
    if latest_weight and first_weight and latest_weight != first_weight:
        weight_change = round(latest_weight.weight_kg - first_weight.weight_kg, 1)

    # Yakilan kalori (manuel)
    burned_calories = profile.burned_calories_manual or 0
    if False and profile.google_fit_token:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            import datetime as dt
            creds = Credentials(
                token=profile.google_fit_token,
                refresh_token=profile.google_fit_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_FIT_CLIENT_ID,
                client_secret=settings.GOOGLE_FIT_CLIENT_SECRET,
            )
            fitness = build('fitness', 'v1', credentials=creds)
            now = dt.datetime.utcnow()
            start = dt.datetime(now.year, now.month, now.day)
            result = fitness.users().dataset().aggregate(
                userId='me',
                body={
                    "aggregateBy": [{"dataTypeName": "com.google.calories.expended"}],
                    "bucketByTime": {"durationMillis": 86400000},
                    "startTimeMillis": int(start.timestamp() * 1000),
                    "endTimeMillis": int(now.timestamp() * 1000),
                }
            ).execute()
            for bucket in result.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        for val in point.get('value', []):
                            burned_calories += val.get('fpVal', 0)
            burned_calories = round(burned_calories)
            if creds.token != profile.google_fit_token:
                profile.google_fit_token = creds.token
                profile.save()
        except Exception as e:
            print(f"Google Fit hata: {e}")

    net_calories = total_cal - burned_calories

    context = {
        'profile': profile,
        'today_meals': today_meals,
        'total_cal': total_cal,
        'burned_calories': burned_calories,
        'net_calories': net_calories,
        'total_protein': round(totals['total_protein'] or 0, 1),
        'total_carbs': round(totals['total_carbs'] or 0, 1),
        'total_fat': round(totals['total_fat'] or 0, 1),
        'goal': goal,
        'progress_pct': progress_pct,
        'remaining': remaining,
        'ring_offset': ring_offset,
        'meals_by_type': meals_by_type,
        'week_data': json.dumps(week_data),
        'weight_data': json.dumps(weight_data),
        'latest_weight': latest_weight,
        'weight_change': weight_change,
        'today': today,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
def ogun_ekle(request):
    if request.method == 'POST':
        form = OgunForm(request.POST, request.FILES)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.user = request.user

            manuel_kalori = form.cleaned_data.get('manuel_kalori')
            manuel_protein = form.cleaned_data.get('manuel_protein')
            manuel_karbonhidrat = form.cleaned_data.get('manuel_karbonhidrat')
            manuel_yag = form.cleaned_data.get('manuel_yag')

            if manuel_kalori:
                meal.total_calories = manuel_kalori
                meal.protein_g = manuel_protein or 0
                meal.carbs_g = manuel_karbonhidrat or 0
                meal.fat_g = manuel_yag or 0
                meal.ai_analysis = "Manuel olarak girildi"
                meal.save()
                messages.success(request, f'Öğün kaydedildi! 🍽️ {meal.total_calories} kcal')
                return redirect('dashboard')

            try:
                analysis = None

                if meal.photo and request.FILES.get('photo'):
                    print("DEBUG: Fotoğraf bulundu, analiz ediliyor...")
                    photo_file = request.FILES['photo']
                    image_data = base64.b64encode(photo_file.read()).decode('utf-8')
                    image_type = photo_file.content_type
                    print(f"DEBUG: Fotoğraf tipi: {image_type}, boyut: {len(image_data)}")

                    analysis = analyze_with_claude(image_data=image_data, image_type=image_type)
                    print(f"DEBUG: Analiz sonucu: {analysis}")

                    if not meal.food_description:
                        items = analysis.get('yemekler', [])
                        if items:
                            meal.food_description = ', '.join([f"{y['isim']} ({y['miktar']})" for y in items])
                        else:
                            meal.food_description = "Fotoğraftan analiz edildi"

                elif meal.food_description:
                    print(f"DEBUG: Metin analizi: {meal.food_description}")
                    analysis = analyze_with_claude(food_text=meal.food_description)
                    print(f"DEBUG: Analiz sonucu: {analysis}")

                if analysis:
                    meal.total_calories = analysis.get('toplam_kalori', 0)
                    meal.protein_g = analysis.get('protein_g', 0)
                    meal.carbs_g = analysis.get('karbonhidrat_g', 0)
                    meal.fat_g = analysis.get('yag_g', 0)
                    meal.ai_analysis = analysis.get('aciklama', '')
                    print(f"DEBUG: Meal kaydediliyor - Kalori: {meal.total_calories}")

                meal.save()
                print(f"DEBUG: Meal kaydedildi - ID: {meal.id}")

                if meal.total_calories == 0:
                    messages.warning(request, '⚠️ API analiz edemedi. Lütfen kalori değerlerini manuel girin.')
                else:
                    messages.success(request, f'Öğün kaydedildi! 🍽️ {meal.total_calories} kcal')

                return redirect('dashboard')

            except Exception as e:
                messages.error(request, f'Hata oluştu: {str(e)}. Lütfen manuel değer girin.')
                meal.save()
                return redirect('dashboard')
    else:
        form = OgunForm(initial={'date': date.today()})

    return render(request, 'tracker/ogun_ekle.html', {'form': form})


@login_required
def ogun_sil(request, pk):
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    meal.delete()
    messages.success(request, 'Öğün silindi.')
    return redirect('dashboard')


@login_required
def gecmis(request):
    filter_date = request.GET.get('tarih')
    meals = Meal.objects.filter(user=request.user)

    if filter_date:
        try:
            from datetime import datetime
            filter_dt = datetime.strptime(filter_date, '%Y-%m-%d').date()
            meals = meals.filter(date=filter_dt)
        except ValueError:
            pass

    meals_list = list(meals)
    grouped = {}
    for meal in meals_list:
        key = meal.date
        if key not in grouped:
            grouped[key] = {'meals': [], 'total_cal': 0}
        grouped[key]['meals'].append(meal)
        grouped[key]['total_cal'] += meal.total_calories

    today = date.today()
    last_7 = today - timedelta(days=7)
    stats = Meal.objects.filter(user=request.user, date__gte=last_7).aggregate(
        total=Sum('total_calories'),
        total_protein=Sum('protein_g'),
        total_carbs=Sum('carbs_g'),
        total_fat=Sum('fat_g'),
        total_macro=Sum('protein_g') + Sum('carbs_g') + Sum('fat_g'),
    )

    meal_count = Meal.objects.filter(user=request.user, date__gte=last_7).count()
    avg_daily = 0
    if stats['total']:
        days_with_meals = Meal.objects.filter(
            user=request.user, date__gte=last_7
        ).values('date').distinct().count()
        avg_daily = int(stats['total'] / max(days_with_meals, 1))

    context = {
        'grouped_meals': sorted(grouped.items(), key=lambda x: x[0], reverse=True),
        'stats': stats,
        'avg_daily': avg_daily,
        'meal_count': meal_count,
        'filter_date': filter_date,
    }
    return render(request, 'tracker/gecmis.html', context)


@login_required
def profil_duzenle(request):
    profile = get_or_create_profile(request.user)

    if request.method == 'POST':
        form = ProfilForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil güncellendi! ✅')
            return redirect('profil_duzenle')
    else:
        form = ProfilForm(instance=profile)

    # BMI hesapla
    analiz = {}
    p = profile
    if p.height_cm and p.weight_kg and p.height_cm > 0:
        h_m = p.height_cm / 100
        bmi = round(p.weight_kg / (h_m ** 2), 1)
        if bmi < 18.5:
            bmi_kategori = 'Zayıf'
            bmi_renk = 'blue'
        elif bmi < 25:
            bmi_kategori = 'Normal'
            bmi_renk = 'green'
        elif bmi < 30:
            bmi_kategori = 'Fazla Kilolu'
            bmi_renk = 'amber'
        else:
            bmi_kategori = 'Obez'
            bmi_renk = 'red'

        # İdeal kilo aralığı (BMI 18.5–24.9)
        ideal_min = round(18.5 * h_m ** 2, 1)
        ideal_max = round(24.9 * h_m ** 2, 1)

        # BMR — Mifflin-St Jeor
        if p.age:
            if p.gender == 'kadin':
                bmr = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age - 161
            else:
                bmr = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age + 5
        else:
            bmr = None

        # TDEE — aktivite çarpanı
        aktivite_carpan = {
            'sedanter': 1.2,
            'hafif': 1.375,
            'orta': 1.55,
            'aktif': 1.725,
            'cok_aktif': 1.9,
        }
        carpan = aktivite_carpan.get(p.activity_level or 'orta', 1.55)
        tdee = round(bmr * carpan) if bmr else None

        # Hedef kalori önerisi
        hedef_kalori_oneri = None
        hedef_yorum = ''
        if tdee and p.target_weight_kg:
            fark = p.target_weight_kg - p.weight_kg
            if fark > 0.5:
                hedef_kalori_oneri = tdee + 300
                hedef_yorum = f'Kilo almak için günde ~{hedef_kalori_oneri} kcal önerilir (+300 surplus)'
            elif fark < -0.5:
                hedef_kalori_oneri = tdee - 500
                hedef_yorum = f'Kilo vermek için günde ~{hedef_kalori_oneri} kcal önerilir (-500 defisit)'
            else:
                hedef_kalori_oneri = tdee
                hedef_yorum = f'Kilonu korumak için günde ~{tdee} kcal önerilir'

        # Hedefe kaç hafta
        hafta_tahmini = None
        if p.target_weight_kg and abs(p.target_weight_kg - p.weight_kg) > 0.5:
            kg_fark = abs(p.target_weight_kg - p.weight_kg)
            hafta_tahmini = round(kg_fark / 0.5)  # haftada ~0.5kg sağlıklı değişim

        # Akıllı yorumlar
        yorumlar = []
        if bmi < 18.5:
            yorumlar.append({'ikon': '⚠️', 'mesaj': f'BMI {bmi} — Zayıf kategorisinde. Kalori alımını artırman önerilir.'})
        elif bmi < 25:
            yorumlar.append({'ikon': '✅', 'mesaj': f'BMI {bmi} — Sağlıklı kilo aralığındasın.'})
        elif bmi < 30:
            yorumlar.append({'ikon': '⚠️', 'mesaj': f'BMI {bmi} — Fazla kilolu kategorisinde. Hafif kalori açığı ve egzersiz önerilir.'})
        else:
            yorumlar.append({'ikon': '🔴', 'mesaj': f'BMI {bmi} — Obez kategorisinde. Bir uzmana danışman önerilir.'})

        if tdee and p.daily_calorie_goal:
            fark_hedef = p.daily_calorie_goal - tdee
            if fark_hedef > 600:
                yorumlar.append({'ikon': '⚠️', 'mesaj': f'Günlük kalori hedefiniz ({p.daily_calorie_goal} kcal) TDEE\'nden {fark_hedef} kcal fazla. Hızlı kilo alımına yol açabilir.'})
            elif fark_hedef < -700:
                yorumlar.append({'ikon': '⚠️', 'mesaj': f'Günlük kalori hedefiniz ({p.daily_calorie_goal} kcal) çok düşük. Kas kaybı riski var.'})
            else:
                yorumlar.append({'ikon': '✅', 'mesaj': f'Kalori hedefiniz ({p.daily_calorie_goal} kcal) TDEE\'nize ({tdee} kcal) göre makul.'})

        if p.target_weight_kg and hafta_tahmini:
            yon = 'almanız' if p.target_weight_kg > p.weight_kg else 'vermeniz'
            yorumlar.append({'ikon': '🎯', 'mesaj': f'Hedef kiloya ({p.target_weight_kg} kg) ulaşmak için tahminen {hafta_tahmini} hafta gerekir.'})

        analiz = {
            'bmi': bmi,
            'bmi_kategori': bmi_kategori,
            'bmi_renk': bmi_renk,
            'ideal_min': ideal_min,
            'ideal_max': ideal_max,
            'bmr': round(bmr) if bmr else None,
            'tdee': tdee,
            'hedef_kalori_oneri': hedef_kalori_oneri,
            'hedef_yorum': hedef_yorum,
            'hafta_tahmini': hafta_tahmini,
            'yorumlar': yorumlar,
        }

    return render(request, 'tracker/profil.html', {
        'form': form,
        'profile': profile,
        'analiz': analiz,
    })


@login_required
def kilo_ekle(request):
    if request.method == 'POST':
        form = WeightLogForm(request.POST)
        if form.is_valid():
            weight_log = form.save(commit=False)
            weight_log.user = request.user

            existing = WeightLog.objects.filter(
                user=request.user,
                date=weight_log.date
            ).first()

            if existing:
                existing.weight_kg = weight_log.weight_kg
                existing.note = weight_log.note
                existing.save()
                messages.success(request, f'Kilo güncellendi! ⚖️ {weight_log.weight_kg} kg')
            else:
                weight_log.save()
                messages.success(request, f'Kilo kaydedildi! ⚖️ {weight_log.weight_kg} kg')

            if weight_log.date == date.today():
                profile = get_or_create_profile(request.user)
                profile.weight_kg = weight_log.weight_kg
                profile.save()

            return redirect('dashboard')
    else:
        initial_data = {'date': date.today()}
        profile = get_or_create_profile(request.user)
        if profile.weight_kg:
            initial_data['weight_kg'] = profile.weight_kg
        form = WeightLogForm(initial=initial_data)

    return render(request, 'tracker/kilo_ekle.html', {'form': form})


@login_required
def kilo_sil(request, pk):
    weight_log = get_object_or_404(WeightLog, pk=pk, user=request.user)
    weight_log.delete()
    messages.success(request, 'Kilo kaydı silindi.')
    return redirect('dashboard')# ── GOOGLE FIT VIEWS ─────────────────────────────────────────

import datetime
from django.http import JsonResponse

@login_required
def google_fit_connect(request):
    from google_auth_oauthlib.flow import Flow
    from django.conf import settings

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                "client_secret": settings.GOOGLE_FIT_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/fitness.activity.read"],
        redirect_uri=settings.GOOGLE_FIT_REDIRECT_URI,
    )

    import secrets, hashlib, base64
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode()

    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        code_challenge=code_challenge,
        code_challenge_method='S256'
    )
    request.session['google_fit_state'] = state
    request.session['google_fit_code_verifier'] = code_verifier
    return redirect(auth_url)


@login_required
def google_fit_callback(request):
    from google_auth_oauthlib.flow import Flow
    from django.conf import settings

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_FIT_CLIENT_ID,
                "client_secret": settings.GOOGLE_FIT_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/fitness.activity.read"],
        redirect_uri=settings.GOOGLE_FIT_REDIRECT_URI,
        state=request.session.get('google_fit_state'),
    )

    code_verifier = request.session.get('google_fit_code_verifier')
    flow.fetch_token(
        authorization_response=request.build_absolute_uri().replace('http://', 'https://'),
        code_verifier=code_verifier
    )
    credentials = flow.credentials

    profile = get_or_create_profile(request.user)
    profile.google_fit_token = credentials.token
    profile.google_fit_refresh_token = credentials.refresh_token if credentials.refresh_token else profile.google_fit_refresh_token
    profile.save()

    messages.success(request, 'Google Fit bağlandı! ✅')
    return redirect('dashboard')


@login_required
def google_fit_calories(request):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from django.conf import settings
    import time

    profile = get_or_create_profile(request.user)

    if not profile.google_fit_token:
        return JsonResponse({'error': 'Google Fit bağlı değil'}, status=400)

    try:
        creds = Credentials(
            token=profile.google_fit_token,
            refresh_token=profile.google_fit_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_FIT_CLIENT_ID,
            client_secret=settings.GOOGLE_FIT_CLIENT_SECRET,
        )

        fitness = build('fitness', 'v1', credentials=creds)

        now = datetime.datetime.utcnow()
        start = datetime.datetime(now.year, now.month, now.day)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(now.timestamp() * 1000)

        body = {
            "aggregateBy": [{"dataTypeName": "com.google.calories.expended"}],
            "bucketByTime": {"durationMillis": 86400000},
            "startTimeMillis": start_ms,
            "endTimeMillis": end_ms,
        }

        result = fitness.users().dataset().aggregate(userId='me', body=body).execute()

        total_calories = 0
        for bucket in result.get('bucket', []):
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for val in point.get('value', []):
                        total_calories += val.get('fpVal', 0)

        return JsonResponse({'burned_calories': round(total_calories)})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def yakilan_kalori_gir(request):
    if request.method == 'POST':
        try:
            miktar = int(float(request.POST.get('burned_calories', 0) or 0))
            if miktar < 0:
                miktar = 0
            profile = get_or_create_profile(request.user)
            profile.burned_calories_manual = miktar
            profile.save()
            messages.success(request, f'🔥 Yakılan kalori güncellendi: {miktar} kcal')
        except Exception as e:
            messages.error(request, f'Hata: {e}')
    return redirect('dashboard')


@login_required
def barkod_ara(request):
    barkod = request.GET.get('barkod', '').strip()
    if not barkod:
        return JsonResponse({'error': 'Barkod girilmedi'}, status=400)

    try:
        import requests as req
        r = req.get(f'https://world.openfoodfacts.org/api/v0/product/{barkod}.json', timeout=5)
        data = r.json()

        if data.get('status') == 1:
            p = data['product']
            n = p.get('nutriments', {})
            urun_adi = p.get('product_name', '') or p.get('product_name_tr', '') or p.get('product_name_en', '')
            kalori_100g = n.get('energy-kcal_100g', 0) or 0
            porsiyon = p.get('serving_size', '100g')

            return JsonResponse({
                'bulundu': True,
                'urun_adi': urun_adi,
                'kalori_100g': round(float(kalori_100g)),
                'protein_100g': round(float(n.get('proteins_100g', 0) or 0), 1),
                'karb_100g': round(float(n.get('carbohydrates_100g', 0) or 0), 1),
                'yag_100g': round(float(n.get('fat_100g', 0) or 0), 1),
                'porsiyon': porsiyon,
            })
        else:
            # Groq ile tahmin et
            analysis = analyze_with_claude(food_text=f'barkod ürünü, barkod no: {barkod}')
            return JsonResponse({
                'bulundu': False,
                'groq_analiz': analysis,
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── ANTRENMAN VIEWS ──────────────────────────────────────────

from .models import WorkoutProgram, Exercise, WorkoutLog, SetLog

@login_required
def antrenman(request):
    programs = WorkoutProgram.objects.filter(user=request.user).prefetch_related('exercises')

    hafta_basi = date.today() - timedelta(days=date.today().weekday())
    bu_hafta_loglar = WorkoutLog.objects.filter(
        user=request.user, date__gte=hafta_basi
    ).values_list('date', flat=True)
    bu_hafta_gun_sayisi = len(set(bu_hafta_loglar))

    # Her program için meta
    program_meta = {}
    for p in programs:
        son = WorkoutLog.objects.filter(user=request.user, program=p).first()
        toplam = WorkoutLog.objects.filter(user=request.user, program=p).count()
        program_meta[p.pk] = {
            'son_tarih': son.date if son else None,
            'toplam_seans': toplam,
        }

    # Haftalık takvim (Pzt-Paz)
    gun_kisalar = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
    bugun_idx = date.today().weekday()

    # Bu haftanın tüm loglarını çek (set detaylarıyla birlikte)
    bu_hafta_tum_loglar = WorkoutLog.objects.filter(
        user=request.user, date__gte=hafta_basi
    ).select_related('program').prefetch_related('sets__exercise').order_by('date')

    # Gün → loglar dict
    gun_log_map = {}
    for log in bu_hafta_tum_loglar:
        d = str(log.date)
        if d not in gun_log_map:
            gun_log_map[d] = []
        gun_log_map[d].append(log)

    # Hafta özeti için JSON (popup'ta kullanılacak)
    hafta_ozet_json = {}
    for log in bu_hafta_tum_loglar:
        d = str(log.date)
        if d not in hafta_ozet_json:
            hafta_ozet_json[d] = []
        egzersizler = []
        for ex in log.program.exercises.all():
            sets = log.sets.filter(exercise=ex).order_by('set_number')
            if sets.exists():
                egzersizler.append({
                    'name': ex.name,
                    'sets': [{'set': s.set_number, 'kg': float(s.weight_kg), 'reps': s.reps} for s in sets]
                })
        hafta_ozet_json[d].append({
            'program': log.program.name,
            'egzersizler': egzersizler,
            'notes': log.notes,
        })

    hafta_gunleri = []
    for i, kisa in enumerate(gun_kisalar):
        gun_tarihi = hafta_basi + timedelta(days=i)
        gun_str = str(gun_tarihi)
        loglar = gun_log_map.get(gun_str, [])
        log_o_gun = loglar[0] if loglar else None
        hafta_gunleri.append({
            'kisa': kisa,
            'tarih': gun_str,
            'bugun': i == bugun_idx,
            'yapildi': bool(loglar),
            'gelecek': gun_tarihi > date.today(),
            'program_adi': log_o_gun.program.name if log_o_gun else None,
            'idx': i,
        })

    return render(request, 'tracker/antrenman.html', {
        'programs': programs,
        'program_meta': program_meta,
        'hafta_gunleri': hafta_gunleri,
        'bu_hafta_gun_sayisi': bu_hafta_gun_sayisi,
        'hafta_ozet_json': json.dumps(hafta_ozet_json, ensure_ascii=False),
        'gun_kisalar_json': json.dumps(gun_kisalar, ensure_ascii=False),
    })


@login_required
def program_ekle(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            program = WorkoutProgram.objects.create(
                user=request.user, name=name, description=description
            )
            messages.success(request, f'✅ {name} programı oluşturuldu!')
            return redirect('program_detay', pk=program.pk)
    return redirect('antrenman')


@login_required
def program_detay(request, pk):
    program = get_object_or_404(WorkoutProgram, pk=pk, user=request.user)
    exercises = program.exercises.all()

    # Haftalık karşılaştırma: her antrenman logunu haftasına göre grupla
    all_logs = WorkoutLog.objects.filter(
        user=request.user, program=program
    ).prefetch_related('sets__exercise').order_by('date')

    def get_week_key(d):
        # ISO hafta: (yıl, hafta_no)
        iso = d.isocalendar()
        return (iso[0], iso[1])

    # Hafta bazında egzersiz → max_kg ve toplam volume
    weekly_data = {}  # {week_key: {ex_pk: {max_kg, total_volume, total_reps, set_count}}}
    week_order = []
    for log in all_logs:
        wk = get_week_key(log.date)
        if wk not in weekly_data:
            weekly_data[wk] = {}
            week_order.append(wk)
        for s in log.sets.all():
            epk = s.exercise_id
            if epk not in weekly_data[wk]:
                weekly_data[wk][epk] = {'max_kg': 0, 'total_volume': 0, 'total_reps': 0, 'set_count': 0}
            d = weekly_data[wk][epk]
            d['max_kg'] = max(d['max_kg'], s.weight_kg)
            d['total_volume'] += s.weight_kg * s.reps
            d['total_reps'] += s.reps
            d['set_count'] += 1

    # Haftalık karşılaştırma listesi (son 8 hafta)
    week_order = week_order[-8:]
    weekly_comparison = []  # [{week_label, ex_pk → {current, prev, diff_kg, diff_vol, trend}}]
    for i, wk in enumerate(week_order):
        prev_wk = week_order[i - 1] if i > 0 else None
        week_label = f"Hafta {i + 1} ({wk[0]}-H{wk[1]})"
        row = {'week_label': week_label, 'week_index': i + 1, 'exercises': {}}
        for ex in exercises:
            epk = ex.pk
            cur = weekly_data[wk].get(epk)
            prev = weekly_data[prev_wk].get(epk) if prev_wk else None
            if cur is None:
                continue
            entry = {
                'max_kg': cur['max_kg'],
                'total_volume': round(cur['total_volume'], 1),
                'total_reps': cur['total_reps'],
                'set_count': cur['set_count'],
                'prev_max_kg': prev['max_kg'] if prev else None,
                'prev_volume': round(prev['total_volume'], 1) if prev else None,
                'diff_kg': None,
                'diff_vol': None,
                'trend': 'new',
            }
            if prev:
                entry['diff_kg'] = round(cur['max_kg'] - prev['max_kg'], 2)
                entry['diff_vol'] = round(cur['total_volume'] - prev['total_volume'], 1)
                if entry['diff_kg'] > 0:
                    entry['trend'] = 'up'
                elif entry['diff_kg'] < 0:
                    entry['trend'] = 'down'
                else:
                    # kg aynı ama volume farklı olabilir
                    if entry['diff_vol'] > 0:
                        entry['trend'] = 'vol_up'
                    elif entry['diff_vol'] < 0:
                        entry['trend'] = 'vol_down'
                    else:
                        entry['trend'] = 'same'
            row['exercises'][epk] = entry
        weekly_comparison.append(row)

    exercise_stats = {}
    for ex in exercises:
        logs = SetLog.objects.filter(
            exercise=ex, workout_log__user=request.user
        ).select_related('workout_log').order_by('workout_log__date')

        sessions = {}
        for s in logs:
            d = str(s.workout_log.date)
            if d not in sessions:
                sessions[d] = {'date': d, 'max_kg': 0, 'total_volume': 0}
            sessions[d]['max_kg'] = max(sessions[d]['max_kg'], s.weight_kg)
            sessions[d]['total_volume'] += s.weight_kg * s.reps

        history = list(sessions.values())[-10:]
        best_kg = max((h['max_kg'] for h in history), default=0)
        first_kg = history[0]['max_kg'] if history else 0
        progress_kg = round(best_kg - first_kg, 2) if len(history) > 1 else 0

        max_kg_all = max((h['max_kg'] for h in history), default=1) or 1
        for h in history:
            h['bar_pct'] = max(8, round((h['max_kg'] / max_kg_all) * 100))

        exercise_stats[ex.pk] = {
            'history': history,
            'best_kg': best_kg,
            'session_count': len(history),
            'progress_kg': progress_kg,
        }

    son_log = WorkoutLog.objects.filter(user=request.user, program=program).first()

    son_log_data = []
    if son_log:
        for ex in exercises:
            sets = son_log.sets.filter(exercise=ex).order_by('set_number')
            if sets.exists():
                son_log_data.append({'exercise': ex, 'sets': list(sets)})

    return render(request, 'tracker/program_detay.html', {
        'program': program,
        'exercises': exercises,
        'exercise_stats': exercise_stats,
        'son_log': son_log,
        'son_log_data': son_log_data,
        'weekly_comparison': weekly_comparison,
        'has_multi_week': len(week_order) >= 2,
    })


@login_required
def egzersiz_sil(request, program_pk, exercise_pk):
    program = get_object_or_404(WorkoutProgram, pk=program_pk, user=request.user)
    exercise = get_object_or_404(Exercise, pk=exercise_pk, program=program)
    exercise.delete()
    messages.success(request, f'🗑️ {exercise.name} silindi.')
    return redirect('program_detay', pk=program_pk)


@login_required
def egzersiz_ekle(request, program_pk):
    program = get_object_or_404(WorkoutProgram, pk=program_pk, user=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', 'diger')
        target_sets = int(request.POST.get('target_sets', 3))
        target_reps = int(request.POST.get('target_reps', 10))
        if name:
            Exercise.objects.create(
                program=program, name=name, category=category,
                target_sets=target_sets, target_reps=target_reps
            )
            messages.success(request, f'✅ {name} eklendi!')
    return redirect('program_detay', pk=program_pk)


@login_required
def antrenman_baslat(request, program_pk):
    program = get_object_or_404(WorkoutProgram, pk=program_pk, user=request.user)
    exercises = program.exercises.all()

    # Tarih parametresi: ?tarih=2026-04-22 gibi geçmiş/gelecek gün için
    tarih_param = request.GET.get('tarih', '')
    try:
        from datetime import datetime
        antrenman_tarihi = datetime.strptime(tarih_param, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        antrenman_tarihi = date.today()

    son_log = WorkoutLog.objects.filter(
        user=request.user, program=program
    ).prefetch_related('sets__exercise').first()

    onceki_setler = {}
    oneri = {}

    if son_log:
        for s in son_log.sets.all():
            key = str(s.exercise.pk)
            if key not in onceki_setler:
                onceki_setler[key] = []
            onceki_setler[key].append({'kg': s.weight_kg, 'reps': s.reps})

        for ex in exercises:
            prev = onceki_setler.get(str(ex.pk), [])
            if not prev:
                continue
            max_kg = max((s['kg'] for s in prev), default=0)
            tum_hedef_tamam = all(s['reps'] >= ex.target_reps for s in prev)
            if tum_hedef_tamam and max_kg > 0:
                artis = 2.5 if max_kg >= 20 else 1.25
                oneri[str(ex.pk)] = {
                    'tip': 'kg', 'onceki_kg': max_kg,
                    'onerilen_kg': max_kg + artis,
                    'mesaj': f'+{artis}kg dene!'
                }
            elif prev:
                max_reps = max((s['reps'] for s in prev), default=0)
                if max_reps < ex.target_reps:
                    oneri[str(ex.pk)] = {
                        'tip': 'reps', 'onceki_reps': max_reps,
                        'hedef_reps': ex.target_reps,
                        'mesaj': f'Hedef: {ex.target_reps} tekrar'
                    }

    return render(request, 'tracker/antrenman_baslat.html', {
        'program': program,
        'exercises': exercises,
        'onceki_setler': json.dumps(onceki_setler),
        'oneri': json.dumps(oneri),
        'antrenman_tarihi': str(antrenman_tarihi),
    })


@login_required
def antrenman_kaydet(request, program_pk):
    if request.method == 'POST':
        program = get_object_or_404(WorkoutProgram, pk=program_pk, user=request.user)

        # Tarih: formdan gelen değeri kullan, yoksa bugün
        tarih_str = request.POST.get('antrenman_tarihi', '')
        try:
            from datetime import datetime
            kayit_tarihi = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            kayit_tarihi = date.today()

        log = WorkoutLog.objects.create(
            user=request.user, program=program,
            date=kayit_tarihi,
            notes=request.POST.get('notes', '')
        )
        for exercise in program.exercises.all():
            set_num = 1
            while True:
                kg_key = f'kg_{exercise.pk}_{set_num}'
                if kg_key not in request.POST:
                    break
                kg = float(request.POST.get(kg_key, 0) or 0)
                reps = int(request.POST.get(f'reps_{exercise.pk}_{set_num}', 0) or 0)
                if kg > 0 or reps > 0:
                    SetLog.objects.create(
                        workout_log=log, exercise=exercise,
                        set_number=set_num, weight_kg=kg, reps=reps
                    )
                set_num += 1
        messages.success(request, '💪 Antrenman kaydedildi!')
        return redirect('antrenman')
    return redirect('antrenman')


@login_required
def program_sil(request, pk):
    program = get_object_or_404(WorkoutProgram, pk=pk, user=request.user)
    program.delete()
    messages.success(request, 'Program silindi.')
    return redirect('antrenman')
