from django.urls import path
from . import views

urlpatterns = [
    path('antrenman/', views.antrenman, name='antrenman'),
    path('antrenman/gecmis/', views.antrenman_gecmis, name='antrenman_gecmis'),
    path('antrenman/program/ekle/', views.program_ekle, name='program_ekle'),
    path('antrenman/program/<int:pk>/', views.program_detay, name='program_detay'),
    path('antrenman/program/<int:pk>/sil/', views.program_sil, name='program_sil'),
    path('antrenman/program/<int:program_pk>/egzersiz/ekle/', views.egzersiz_ekle, name='egzersiz_ekle'),
    path('antrenman/program/<int:program_pk>/egzersiz/<int:exercise_pk>/sil/', views.egzersiz_sil, name='egzersiz_sil'),
    path('antrenman/program/<int:program_pk>/egzersiz/<int:exercise_pk>/duzenle/', views.egzersiz_duzenle, name='egzersiz_duzenle'),
    path('antrenman/program/<int:program_pk>/baslat/', views.antrenman_baslat, name='antrenman_baslat'),
    path('antrenman/program/<int:program_pk>/kaydet/', views.antrenman_kaydet, name='antrenman_kaydet'),
    path('yakilan-kalori/', views.yakilan_kalori_gir, name='yakilan_kalori_gir'),
    path('google-fit/connect/', views.google_fit_connect, name='google_fit_connect'),
    path('google-fit/callback/', views.google_fit_callback, name='google_fit_callback'),
    path('google-fit/calories/', views.google_fit_calories, name='google_fit_calories'),
    path('', views.dashboard, name='dashboard'),
    path('giris/', views.giris, name='giris'),
    path('kayit/', views.kayit, name='kayit'),
    path('cikis/', views.cikis, name='cikis'),
    path('ogun/ekle/', views.ogun_ekle, name='ogun_ekle'),
    path('ogun/sil/<int:pk>/', views.ogun_sil, name='ogun_sil'),
    path('kilo/ekle/', views.kilo_ekle, name='kilo_ekle'),
    path('kilo/sil/<int:pk>/', views.kilo_sil, name='kilo_sil'),
    path('gecmis/', views.gecmis, name='gecmis'),
    path('profil/', views.profil_duzenle, name='profil_duzenle'),
]
