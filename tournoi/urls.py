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

    path('multiequipe/<str:pattern>/', views.multiequipe, name='multi-team'),
    path('multiequipe/', views.multiequipe, name='multi-team'),

    # The page displaying the competition
    path('competition/<str:compet>/', views.competition_detail, name='comp-detail'),

    # The URL that triggers your extraction script
    path('competition/<str:compet>/extract/', views.extract_matches, name='comp-extract'),

    # domain.com/maj_divers/ --- OBSOLETE ? à vérifier
    path('maj_divers/', views.maj_divers, name='maj_divers'),

    path('timeout/<str:pattern>/', views.timeout, name='timeout'),

    # "internal API endpoint: update a single match"
    path('competition/<str:compet>/update/<str:match_id>/', views.update_single_match, name='match-update'),

    path('create_match_data/', views.create_match_data, name='create_match_data'),
    path('maj_member_count/', views.maj_member_count, name='maj_member_count'),
    path('maj_participation/', views.maj_participation, name='maj_participation'),

    path('rename-club/', views.rename_club, name='rename_club'),

    # this updated Match.name from raw_data -- no more needed, now done in Match.save()
    path('update-match-names/', views.update_match_names, name='update_match_names'),
    path('<str:pattern>/', views.homepage, name='home'),
    path('api/receive-links/', views.bookmarklet_receiver, name='bookmarklet_receiver'),
]
