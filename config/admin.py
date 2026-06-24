from django.contrib.admin import AdminSite
from django.urls import reverse


class VodopadAdminSite(AdminSite):
    site_header = 'Администрирование Vodopad'
    site_title = 'Vodopad Admin'
    index_title = 'ADMIN'

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request)
        models = [model for app in app_list for model in app['models']]
        models.sort(key=lambda model: model['name'].lower())

        if not models:
            return []

        return [{
            'name': 'ADMIN',
            'app_label': 'admin',
            'app_url': reverse('admin:index'),
            'has_module_perms': True,
            'models': models,
        }]
