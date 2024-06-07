from django.contrib import admin

from .models import Book, Account, Contact, Opportunity, Adoption

class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    search_fields = ("name", "id")
    list_filter = ("type", "created_date", "last_modified_date")

admin.site.register(Account, AccountAdmin)

class BookAdmin(admin.ModelAdmin):
    list_display = ("name", "official_name", "type", "subject_areas", "website_url")
    search_fields = ("name", "official_name", "type", "subject_areas", "website_url")
    list_filter = ("type", "subject_areas")

admin.site.register(Book, BookAdmin)

class ContactAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "position", "account")
    search_fields = ("full_name", "role", "position", "account")

admin.site.register(Contact, ContactAdmin)

class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "stage_name")
    search_fields = ("name", "account")
    list_filter = ("stage_name", )

admin.site.register(Opportunity, OpportunityAdmin)

class AdoptionAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "confirmation_type")
    search_fields = ("book", )
    list_filter = ("confirmation_type", )

admin.site.register(Adoption, AdoptionAdmin)
