from django.contrib import admin
from .models import Dataset

class DatasetAdmin(admin.ModelAdmin):
    # Customize the display of the Dataset model in the admin panel
    list_display = ('file', 'uploaded_at', 'file_hash', 'compare_with')
    search_fields = ('file_hash',)  # Allow searching by file hash for easy lookup

admin.site.register(Dataset, DatasetAdmin)
