from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('public.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('accounts.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/', include('prediction.urls')),
    path('banking/', include('banking.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Also serve from STATICFILES_DIRS
    from django.views.static import serve
    urlpatterns += [
        path('static/<path:path>', serve, {'document_root': settings.STATICFILES_DIRS[0]}),
    ]