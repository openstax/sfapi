from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('account_uuid', 'email')


admin.site.register(get_user_model(), UserAdmin)
admin.site.unregister(Group)
