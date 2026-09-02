from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from django.views.generic.base import RedirectView

def unregister_service_worker(request):
    js = """
    self.addEventListener('install', function(e) { self.skipWaiting(); });
    self.addEventListener('activate', function(e) {
        self.registration.unregister().then(function() {
            return self.clients.matchAll();
        }).then(function(clients) {
            clients.forEach(client => client.navigate(client.url));
        });
    });
    """
    return HttpResponse(js, content_type='application/javascript')

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/dms/img/favicon.ico', permanent=False)),
    path('admin/', admin.site.urls),
    path('sw.js', unregister_service_worker),
    path('service-worker.js', unregister_service_worker),
    path('', include('dms.urls')),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
