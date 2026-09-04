# tournoi/urls.py
from django.urls import path
from . import views
app_name = 'tournoi'
urlpatterns = [
    # Homepage.
    path('', views.homepage, name='home'),
    # But the same page is also reached e.g. for /cfe, /lfr, /CFT/ ...
    # and more generally any '<str:pattern>/' (see very last entry on bottom of this list)
    # which doesn't match the earlier "static" pages.
    # However, IN CASE we would like to use pattern = something that equals another path,
    # we define the following which allows us to "send" any pattern
    #path('home/<str:pattern>/', views.homepage, name='home'),

    path('top10/', views.top10, name='top10'),  # Records de participation
    path('clubs/', views.clubs, name='clubs'),  # liste des Clubs

    # TABLEAU DE CLASSEMENT : p.ex. cfe.pythonanywhere.com/classement/CFE 2026 D1/
    path('classement/<str:compet>/', views.classement, name='classement'),

    # Joueurs multi-équipe ##  LOGIN REQUIRED
    path('multiequipe/<str:pattern>/', views.multiequipe, name='multi-team'),
    path('multiequipe/', views.multiequipe, name='multi-team'),

    # display "details" of a competition (in particular, the list/table of matches)
    path('competition/<str:compet>/', views.competition_detail, name='comp-detail'),

    # "extraction script" -- extract "match links" from HTML code.
    # This is "called" by the JS when the user pasted the HTML code into the "textarea"
    path('competition/<str:compet>/extract/', views.extract_matches, name='comp-extract'),

    # domain.com/maj_divers/ --- OBSOLETE ? à vérifier
    path('maj_divers/', views.maj_divers, name='maj_divers'),

    # Liste des parties perdues au temps (par joueur, par compet)
    path('timeout/<str:pattern>/', views.timeout, name='timeout'),

    # internal API endpoint: update a single match
    # Called by the JS for each match in the list/table, when clicking "Rencontres [actualiser]"
    path('competition/<str:compet>/update/<str:match_id>/', views.update_single_match, name='match-update'),

    # This "API" sends a JsonResponse which contains the data allowing the bookmarklet
    # to fill in the match creation form
    path('create_match_data/', views.create_match_data, name='create_match_data'),

    path('maj_member_count/', views.maj_member_count, name='maj_member_count'),
    path('maj_participation/', views.maj_participation, name='maj_participation'),

    path('rename-club/', views.rename_club, name='rename_club'),

    # this updated Match.name from raw_data -- no more needed, now done in Match.save()
    path('update-match-names/', views.update_match_names, name='update_match_names'),
    path('api/receive-links/', views.bookmarklet_receiver, name='bookmarklet_receiver'),
    path('api/next-match/', views.api_next_match, name='api_next_match'),

    # This comes last because it's "catch_all"
    path('<str:pattern>/', views.homepage, name='home'),
]
