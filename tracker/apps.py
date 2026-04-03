from django.apps import AppConfig

class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'
    verbose_name = 'Kalori Takip'
    
    def ready(self):
        import tracker.signals
