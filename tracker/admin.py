from django.contrib import admin
from .models import UserProfile, Meal, WeightLog

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'daily_calorie_goal', 'weight_kg', 'target_weight_kg']

@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ['user', 'meal_type', 'date', 'total_calories', 'food_description']
    list_filter = ['meal_type', 'date']

@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'weight_kg', 'date', 'note']
    list_filter = ['date', 'user']
    ordering = ['-date']
