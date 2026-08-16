"""
URL configuration for mysite_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
#from tournoi import views as tournoi_views # do this through include(...) below

urlpatterns = [
    path("admin/", admin.site.urls),
    # The line below is superseeded
    #path('', tournoi_views.homepage, name='home'),  # Route the root URL to your function
    path('' #'tournoi/'
        , include('tournoi.urls')),  # Route the root URL to your function
    # NEW URL: The JavaScript will ping this address
    # now also moved into 'tournoi.urls'
    #path('api/get-matches/', views.fetch_chess_data, name='get_matches'),
]
