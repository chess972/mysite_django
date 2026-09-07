# tournoi/urls.py
from django.urls import path
from . import views
app_name = 'tournoi'
urlpatterns = [
    # 1. PUBLIC PAGES

    # Homepage:
    path('', views.homepage, name='home'),
    # The same page is also shown for /cfe, /lfr, /CFT, and any '<str:pattern>/'
    # to list a subset of competitions matching `pattern` (which must not match
    # and of the earlier "static" pages), see very last entry of this list.

    # IN CASE we would like to use pattern = something that equals another path,
    # we define the following which allows us to "transmit" any pattern
    # path('home/<str:pattern>/', views.homepage, name='home'),

    # TABLEAU DE CLASSEMENT : p.ex. cfe.pythonanywhere.com/classement/CFE 2026 D1/
    path('classement/<str:compet>/', views.classement, name='classement'),

    # display details of a competition (in particular, the list/table of matches)
    path('competition/<str:compet>/', views.competition_detail, name='comp-detail'),

    path('top10/', views.top10, name='top10'),  # Records de participation
    path('clubs/', views.clubs, name='clubs'),  # liste des Clubs

    # 2. ADMIN PAGES -- login required

    # Joueurs multi-équipe ##  LOGIN REQUIRED
    path('multiequipe/<str:pattern>/', views.multiequipe, name='multi-team'),
    path('multiequipe/', views.multiequipe, name='multi-team'),

    # Liste des parties perdues au temps (par joueur, par compet)
    path('timeout/<str:pattern>/', views.timeout, name='timeout'),

    path('bookmarklets/', views.bookmarklets, name='bookmarklets'),

    # these redirect to the club page
    path('maj_member_count/', views.maj_member_count, name='maj_member_count'),
    path('maj_participation/', views.maj_participation, name='maj_participation'),

    ### 3. API ### (not really "pages", usually send back Json and/or update database

    # "extraction script" -- extract "match links" from HTML code.
    # This is "called" by the JS when the user pasted the HTML code into the "textarea"
    path('competition/<str:compet>/extract/', views.extract_matches, name='comp-extract'),

    # internal API endpoint: update a single match
    # Called by the JS for each match in the list/table, when clicking "Rencontres [actualiser]"
    path('competition/<str:compet>/update/<str:match_id>/', views.update_single_match, name='match-update'),

    # this updated Match.name from raw_data -- no more needed, now done in Match.save()
    path('update-match-names/', views.update_match_names, name='update_match_names'),
    path('api/receive-links/', views.bookmarklet_receiver, name='bookmarklet_receiver'),

    # This "API" sends a JsonResponse which contains the data allowing the
    # JS bookmarklet to fill in the match creation form
    path('api/next-match/', views.api_next_match, name='api_next_match'),

    # This "API" sends a JsonResponse which contains the data allowing the
    # tampermonkey script to fill in the match creation form
    path('create_match_data/', views.api_next_match, name='create_match_data'),

    ### 4. OBSOLETE ### (ou presque ?)

    # not useful currently: better use django admin interface
    path('rename-club/', views.rename_club, name='rename_club'),

    # domain.com/maj_divers/ --- OBSOLETE ? à vérifier
    path('maj_divers/', views.maj_divers, name='maj_divers'),

    ### 5. catch-all : => homepage, with "path" as argument (=: pattern)

    path('<str:pattern>/', views.homepage, name='home'), # must be last in the list (matches anything)
]
