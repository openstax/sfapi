from django.contrib import admin

from .models import Book, Account, Contact, Opportunity, Adoption

class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "is_deleted")
    search_fields = ("name", "id")
    list_filter = ("type", "is_deleted", "created_date", "last_modified_date")

    def get_queryset(self, request):
        return Account.all_objects.all()

admin.site.register(Account, AccountAdmin)

class BookAdmin(admin.ModelAdmin):
    list_display = ("name", "official_name", "type", "subject_areas", "website_url", "is_deleted")
    search_fields = ("name", "official_name", "type", "subject_areas", "website_url")
    list_filter = ("type", "is_deleted", "subject_areas")

    def get_queryset(self, request):
        return Book.all_objects.all()

admin.site.register(Book, BookAdmin)

class ContactAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "position", "account", "is_deleted")
    search_fields = ("full_name", "role", "position", "account")
    raw_id_fields = ("account", )
    list_filter = ("is_deleted",)

    def get_queryset(self, request):
        return Contact.all_objects.all()

admin.site.register(Contact, ContactAdmin)

class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "stage_name")
    search_fields = ("name", "account")
    list_filter = ("stage_name", )
    raw_id_fields = ("account", )

admin.site.register(Opportunity, OpportunityAdmin)

class AdoptionAdmin(admin.ModelAdmin):
    list_display = ("contact", "opportunity", "confirmation_type")
    search_fields = ("contact", "opportunity__book")
    list_filter = ("confirmation_type", "opportunity__book")
    raw_id_fields = ("opportunity", "contact")

admin.site.register(Adoption, AdoptionAdmin)
