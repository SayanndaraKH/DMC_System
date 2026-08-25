from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

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
    path('admin/', admin.site.urls),
    path('sw.js', unregister_service_worker),
    path('service-worker.js', unregister_service_worker),
    path('', include('dms.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
