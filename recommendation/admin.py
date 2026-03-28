from django.contrib import admin
from .models import BrowseHistory, UserBehavior

admin.site.register(BrowseHistory)
admin.site.register(UserBehavior)
