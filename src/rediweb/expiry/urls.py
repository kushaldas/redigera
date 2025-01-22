from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload", views.upload_file, name="upload_file"),
    path("update_expiry", views.update_expiry, name="update_expiry"),
    path("key_ready", views.key_ready, name="key_ready"),
    path("getyubikey", views.getyubikey, name="getyubikey"),
    path("expiry", views.expiry, name="expiry"),
]
