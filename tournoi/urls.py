# tournoi/urls.py
from django.urls import path
from . import views
app_name = 'tournoi'
urlpatterns = [
    # domain.com/
    path('', views.homepage, name='home'),
    path('home/<str:pattern>/', views.homepage, name='home'),

    path('top10/', views.top10, name='top10'),

    path('clubs/', views.clubs, name='clubs'),

    # domain.com/classement/CFE 2026 D1/ : tableau de classement
    path('classement/<str:compet>/', views.classement, name='classement'),

    # The page displaying the competition
    path('competition/<str:compet>/', views.competition_detail, name='comp-detail'),

    # The URL that triggers your extraction script
    path('competition/<str:compet>/extract/', views.extract_matches, name='comp-extract'),

    # domain.com/maj_club_abbrevs/
    path('maj_club_abbrevs/', views.maj_club_abbrevs, name='maj_club_abbrevs'),

    # "internal API endpoint: update a single match"
    path('competition/<str:compet>/update/<str:match_id>/', views.update_single_match, name='match-update'),

    path('rename-club/', views.rename_club, name='rename_club'),
    path('update-match-names/', views.update_match_names, name='update_match_names'),
    path('<str:pattern>/', views.homepage, name='home'),

]
