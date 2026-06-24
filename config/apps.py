from django.contrib.admin.apps import AdminConfig


class VodopadAdminConfig(AdminConfig):
    default_site = 'config.admin.VodopadAdminSite'

    def ready(self):
        super().ready()

        from django.contrib import admin
        from django.contrib.auth.models import Group

        if admin.site.is_registered(Group):
            admin.site.unregister(Group)
