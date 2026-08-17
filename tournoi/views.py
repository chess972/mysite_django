# tournoi/views.py - (c) 2026 by MFH
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
#from django.core.cache import cache
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.db.models import F,Q # for top10
from datetime import date,datetime # for current_year in top10
from contextlib import redirect_stdout
from .models import Competition, Match, Club
from .services import calcul_classement, update_match, extract_match_ids_from_HTML # extract_match_ids_from_web
import io

#    path('classement/<str:compet>/', views.classement, name='classement'),
def classement(request, compet: str):
    # This looks up the Competition where name matches the URL
    if "_" in compet: compet = compet.replace("_", " ")
    if competition := get_object_or_404(Competition, name=compet):
        classements = calcul_classement(competition) # from tournoi.services
    context = {
        'compet': competition or compet,
        'classements': classements,
    }
    return render(request, 'tournoi/classement.html', context)

# path('clubs/', views.clubs, name='clubs'),
def clubs(request):
    clubs = Club.objects.order_by('name')
    return render(request, 'tournoi/clubs.html', {'clubs': clubs})

# path('maj_club_abbrevs/', views.maj_club_abbrevs, name='maj_club_abbrevs'),
@staff_member_required
def maj_club_abbrevs(request):
    from tournoi.utils import update_club_abbrevs
    output=["<h2>Mise à jour des abbreviations de clubs...</h2>"]
    buffer = io.StringIO() ; pre = 0
    with redirect_stdout(buffer): update_club_abbrevs()
    def end_pre():
        nonlocal pre, output
        if pre: output += ["</pre>"]; pre=0 # switch off
    for line in buffer.getvalue().splitlines():
        if line.startswith('<'): end_pre() # HTML
        elif not pre: output += ["<pre>"]; pre=1 # if not HTML & not pre, switch on
        output += [line]
    end_pre()
    if len(output) > 2:
        output += ["<p>Vérifiez <a href='/clubs'>sur la page 'Clubs'</a> que les abbréviations sont adéquates et uniques !</p>"]
    output=["<h2>Mise à jour des noms longs de clubs...</h2>"]

    unnamed_clubs = Club.objects.exclude(raw_data__has_key='name')
    unnamed_ids = set(unnamed_clubs.values_list('id', flat=True))
    for m in Match.objects.filter(raw_data__has_key='teams').iterator():
            if not unnamed_ids: break
            for team in ((m.raw_data or {}).get('teams') or {}).values():
                club_id = team.get('@id','').split('/')[-1]
                if club_id in unnamed_ids and (name := team.get('name')):
                    club = unnamed_clubs.filter(id=club_id).first()
                    if club.raw_data: club.raw_data['name'] = name
                    else: club.raw_data = {'name': name}
                    club.save(update_fields=['raw_data'])
                    output += [f"Added long name for {club.name} ({club_id}): {name}<br/>" ]
                    unnamed_ids . remove(club_id)
            if not unnamed_ids: break
    output += [ "Done." ]
    return render(request, 'tournoi/simple_output.html', {'lines': output} )

# path('top10/', views.top10, name='top10'),
def top10(request):
    current_year = str(date.today().year)
    # Base queryset sorted by num_boards DESC (top 10)
    matches = Match.objects.annotate(
            finished=F('score_team1') + F('score_team2')
        ).order_by( '-num_boards', '-finished',
                    F('raw_data__end_time').asc(nulls_last=True))
    # optional: Exclude hidden competitions for non-superusers
    # no-- we may want to hide copetitions in the list on the "admin" page
    # but not the "all times best" matches.
    #if not request.user.is_superuser:
    #    matches = matches.filter(competition__hidden=False)
    top10 = {'': {  "name": "Général - Toutes catégories",
                    "matches": matches[:10] },
            'CFE': { 'name': 'Championnat de France par Équipe (CFE)'},
            'LFR': { 'name': 'Ligue Française des Régions (LFR)'},
            'CFT': { 'name': 'Coupe de France des Territoires (CFT)'},
        }
    matches = matches.filter(name__icontains=current_year)
    for code,data in top10.items():
        if code: data['matches'] = matches.filter(name__icontains=code)[:10]
    return render(request, 'tournoi/top10.html', {'sections': top10 })

#    path('rename-club/', views.rename_club, name='rename_club'),
@staff_member_required
def rename_club(request):
    data = request.POST or request.GET
    old_name = data.get('old_name', '').strip()
    new_name = data.get('new_name', '').strip()
    if (dont_ask_again := data.get('dont_ask_again', ''))=='1':
        #User clicked "Oui, renommer" with no change : do rename
        if old_name and new_name:
            count = Club.objects.filter(name=old_name).update(name=new_name)
            messages.success(request, f"Succès : {count} club(s) renommé(s) de '{old_name}' vers '{new_name}'.")
            return redirect('tournoi:home')  # Redirect back to homepage
    elif dont_ask_again:
        messages.warning(request, f"Attention: noms changés! Merci de re-confirmer!")
    return render(request, 'tournoi/confirm_rename.html', {
        'old_name': old_name, 'new_name': new_name,
    })

#path('update-match-names/', views.update_match_names, name='update_match_names'),
@staff_member_required
def update_match_names(request):
    if request.method == 'POST':
        # Find matches where name is either NULL or an empty string
        unnamed_matches = Match.objects.filter(Q(name__isnull=True) | Q(name=''))
        updated_count = 0
        for match in unnamed_matches:
            if api_name := match.raw_data.get('name') if match.raw_data else None:
                match.name = api_name
                match.save(update_fields=['name'])
                updated_count += 1
        if updated_count:
            messages.success(request, f"{updated_count} nom(s) de match mis à jour depuis raw_data.")
        else:
            messages.info(request, "Aucun nom de match à mettre à jour.")
    # Redirect back to the page the user clicked the button from
    return redirect(request.META.get('HTTP_REFERER', 'tournoi:home'))

### code for updating and displaying details of a competition

# The page displaying the competition
# path('competition/<str:compet>/', views.competition_detail, name='comp-detail'),
def competition_detail(request, compet):
    # Fetch the competition and all its matches (using your related_name)
    comp = get_object_or_404(Competition, name=compet)
    matches = comp.matches.all()
    ## Inside competition_detail view...
    matches_to_update = list(comp.matches.exclude(status='finished').values_list('id', flat=True))
    # Pass this list into the context dictionary alongside 'comp' and 'matches'

    return render(request, 'tournoi/comp_detail.html', {'comp': comp, 'matches': matches,
        'matches_to_update':matches_to_update})

# The URL that triggers the extraction script
# path('competition/<str:compet>/extract/', views.extract_matches, name='comp-extract'),
@staff_member_required
def extract_matches(request, compet):
    # Security check: Only allow POST requests (button clicks)
    if request.method == "POST":
        comp = get_object_or_404(Competition, name=compet)
        # currently , trying to access www.chess.com crashes the script (not authorized by PythonAnywhere)
        # so we can't use:
        # if match_ids := extract_match_ids_from_web(comp.url): # defined in services.py
        # but instead we have to use:
        if pasted_html := request.POST.get('pasted_html', ''):
          #messages.info(request, f"{len(pasted_html) = }")
          if match_ids := extract_match_ids_from_HTML(pasted_html): # defined in services.py
            raw_data = {} ; date = None
            if not isinstance( match_ids[0], str ): # cut-off date
                cutoff_dates = match_ids.pop(0)
                #messages.info(request, f"Debug: {cutoff_dates = }")
                #if request.user.is_superuser: ## anyways, this is accessible only for staff
                other_info = {k:v for k,v in cutoff_dates.items() if '01' > k or k > '32'}
                if cutoff_dates := {k:v for k,v in cutoff_dates.items() if '01' < k < '32'}:
                #    date = max(cutoff_dates, key = lambda d: cutoff_dates[d]if '0'<=d<='9'else 0)
                    if len( cutoff_dates ) > 1:
                        messages.warning(request, f"Différents {cutoff_dates = }.")
                        if not comp.raw_data: comp.raw_data={'cutoff_dates': cutoff_dates}
                        else: comp.raw_data['cutoff_dates'] = comp.raw_data.get('cutoff_dates',{}) | cutoff_dates
                        comp.save()
                    elif date := min(cutoff_dates):
                        messages.success(request, f"Date de cut-off détectée: {date}.")
                        try:
                            comp.cutoff_date = datetime.strptime(date, "%d/%m/%Y")
                            comp.save()
                        except (ValueError, TypeError):
                            messages.error(request, f"N'ai pu interpréter/stocker la date de cut-off.")
                else:
                    messages.info(request, f"Pas de date de cut-off détectée.")
            messages.success(request, f"{len(match_ids)} rencontres détectées.")
            # Save to database
            for m_id in match_ids:
                # get_or_create prevents duplicates if the button is clicked twice
                # BUT we can get an exception if the same match is linked to a different competition!
                try: Match.objects.get_or_create( id=m_id, competition=comp,
                        defaults={'name': '', 'status': ''} #or: status=='unknown' ?
                    )
                except: m_id = '0'+m_id ; Match.objects.get_or_create(id=m_id, competition=comp,
                        defaults={'name': '', 'status': ''} #or: status=='' ?
                    ) ;  messages.warning(request, f"ATTENTION: Match '{m_id}' en double - informez un admin!")

          else:
            messages.error(request, f"Impossible d'extraire la liste des rencontres.")# de l'URL {comp.url}
            match_ids=()
        else:
            messages.error(request, f"Pas de HTML reçu.")# de l'URL {comp.url}
        # Redirect back to the detail page so the user sees the new data
        return redirect('tournoi:comp-detail', compet=comp.name)

#ngle-match update view.
#This view takes one match ID, hits the CC API, updates the database, and returns JSON.
#path('competition/<str:compet>/update/<str:match_id>/', views.update_single_match, name='match-update'),
@staff_member_required
def update_single_match(request, compet, match_id):
    if request.method != "POST": return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)
    try: match = Match.objects.get(id=match_id) #, competition__name=comp_name)
    except Match.DoesNotExist: return JsonResponse({ 'status': 'error',
            'message': f'Match {match_id} missing from DB during Level 2 update.'
        }, status=404)
    # Only ping the API if the match isn't finished
    # (TODO: implement "expiry"/"last_updated" timestamp)
    if match.status != 'finished':
        if error := update_match(match):
            messages.error(request, error)
            return JsonResponse({ 'status': 'error', 'message': error }, status=404)
    match_data={key: getattr(match, key) for key in (
        "status","team1_id","team2_id","score_team1","score_team2","num_boards", "remaining")}
    return JsonResponse({'status': 'success', 'match_id': match_id, 'data': match_data})

#    path('', views.homepage, name='home'),
#    path('<str:pattern>/', views.homepage, name='home'),
def homepage(request, pattern=''):
    if request.method == "POST":
        # 1. Ajouter une compétition
        if 'ajout_compet' in request.POST:
            new_compet = request.POST.get('new_compet', '').strip()
            compet_url = request.POST.get('compet_url', '').strip()

            if new_compet and compet_url:
                if Competition.objects.filter(name=new_compet).exists():
                    messages.error(request, f"La compétition '{new_compet}' existe déjà!")
                else:
                    Competition.objects.create(name=new_compet, url=compet_url)
                    messages.success(request, f"OK - compétition '{new_compet}' ajoutée!")
            else:
                messages.error(request, "Pour ajouter une nouvelle compétition, indiquer le sigle et l'URL.")

        # 2. Choisir une compétition
        elif 'choix_compet' in request.POST:
            choix = request.POST.get('choix_compet')
            request.session['compet'] = choix
            messages.success(request, f"OK - compétition '{choix}' choisie!")

        # 3. Supprimer une compétition
        elif 'del_compet' in request.POST:
            del_target = request.POST.get('del_compet')
            if c := Competition.objects.filter(name=del_target).update(hidden=True): # was:delete()
                # now, c = number of affected records
                # or:  ...first() : c.hidden = True; c.save()
                if request.session.get('compet') == del_target:
                    request.session.pop('compet', None)
                messages.success(request, f"OK - compétition '{del_target}' cachée!")
            else: messages.error(request, f"Compétition '{del_target}' non trouvée!")

        # 4. Détails d'une compétition
        elif 'detail_compet' in request.POST:
            det_target = request.POST.get('detail_compet')
            comp = Competition.objects.filter(name=det_target).first()
            if comp:
                messages.info(request, f"Compétition '{comp.name}': URL={comp.url}")
            else:
                messages.error(request, f"La compétition '{det_target}' n'est plus dans la base!")

        # 5. Calculer le tableau
        elif 'tableau' in request.POST:
            tableau_target = request.POST.get('tableau')
            # make_table(tableau_target) ...
            messages.success(request, f"Tableau calculé pour {tableau_target}")

        return redirect('tournoi:home'  # Redirect prevents double form submission on refresh!
            if not pattern else f"{reverse('tournoi:home')}{pattern}/")
    # GET Request: was a particular competition selected?
    if pattern:
        # allow "sluggish" competition names
        if "-" in pattern: pattern.replace("-"," ")
        competitions = Competition.objects.filter(name__istartswith=pattern)
        if not competitions: return render(request, 'tournoi/simple_output.html', {
            'title': f'Aucune compétition dont le nom correspond au {pattern = !r}!'})
    else:
        competitions = Competition.objects.all()
    # Prepare data for rendering
    matches_to_update = selected_compet = None
    if selected_name := request.session.get('compet'):
        if selected_compet := competitions.filter(name=selected_name).first():
            if request.user.is_superuser:
                matches_to_update = list(selected_compet.matches.exclude(
                    status='finished').values_list('id', flat=True))
    context = {
        'competitions': competitions, 'pattern': vars().get('pattern'),
        'selected_compet': selected_compet, 'matches_to_update':matches_to_update
    }
    return render(request, 'tournoi/cfe.html', context)
