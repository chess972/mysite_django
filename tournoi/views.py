# tournoi/views.py - (c) 2026 by MFH

from contextlib import redirect_stdout
from datetime import date,datetime # for current_year in top10
import io
import json

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
#from django.core.cache import cache
#from django.db import IntegrityError
from django.db.models import F,Q # for top10
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Competition, Match, Club
from . import services
# get_next_match, compute_multiteam, calcul_classement, update_match, create_matches, extract_match_ids_from_HTML

# path('api/next-match/', views.api_next_match, name='api_next_match'),
def api_next_match(request, pattern=''):
    """Return Json with data for filling in the form at chess.com, to create the next competition."""
    if"_"in pattern: pattern = pattern.replace("_"," ")
    for comp in Competition.objects.filter(status__startswith="incomplet", name__icontains=pattern):
        if response := services.get_next_match(comp): # from services
            return response
    return JsonResponse({ 'status': 'error', 'message':
        f"Aucun match à programmer trouvé pour {pattern = !r}" if pattern
        else "Aucun match à programmer trouvé !"
        }, status=404)


#    path('multiequipe/<str:compet>/', views.multiequipe, name='multi-team'),
@login_required
def multiequipe(request, pattern=''):
    """Etablir la liste des "joueurs multi-équipe", qui jouent (ou se sont inscrits)
    pour plus qu'un seul club au sein de la même compétition."""
    if not pattern: pattern = (request.POST or request.GET).get('pattern') or ''
    if'_'in pattern: pattern = pattern.replace('_',' ')
    return render(request, "tournoi/multi-team.html", {'pattern':pattern.upper(),
        'players': services.compute_multiteam(pattern) if len(pattern)==8 or pattern and request.user.is_superuser
        else ['<dt>Nom de compétition invalide !<dd>Le nom doit être de la forme "CFE 2026" ou similaire.']
    })

#    path('maj_member_count/', views.maj_member_count, name='maj_member_count'),
@login_required
def maj_member_count(request):
    "Actualiser le nombre de membres [chess.com vs notre BDD] de tous les clubs."
    for club in Club.objects.all():
        club.update_from_api(exclude='description') # we don't want the long description
    return redirect('tournoi:clubs')

# Sur la page /clubs, lien "Participation"
#    path('maj_participation/', views.maj_participation, name='maj_participation'),
@login_required
def maj_participation(request):
    """Ajoute/actualise, dans chaque `Club.raw_data`, une entrée `participation`
    qui donne le nombre de rencontres dans lesquelles le club a participé,
    et le domaine d'années, par exemple: "17 CFE, 1 CFT, 14 LFR, 2023–2026"."""
    from collections import defaultdict
    club = {}
    for match in Match.objects.all():
        comp = match.competition
        for t in (match.team1_id, match.team2_id):
            if not(d:=club.get(t)): d=club[t]=defaultdict(int,{'min_year':9999}) #'max_year':0,'CFE':0,'CFT':0,'LFR':0,
            if d['min_year'] > comp.year: d['min_year'] = comp.year
            if d['max_year'] < comp.year: d['max_year'] = comp.year
            d[comp.name[:3]] += 1
    for c in Club.objects.all():
        if d:=club.get(c.id):
            if d['CVF']: d['CFT'] += d['CVF']
            c.raw_data['participation']=", ".join(f"{d[t]} {t}"for t in('CFE','CFT','LFR'
                ) if d[t]) + f", {d['min_year']}–{d['max_year']}" # &ndash; will be escaped in DTL
            c.save(update_fields=['raw_data'])
    return redirect('tournoi:clubs')


@login_required
#    path('timeout/<str:pattern>/', views.timeout, name='timeout'),
def timeout(request, pattern:str):
    """Affiche un tableau avec les match perdues par timeout, pour un joueur donné.
    players = dict {player_id : [lost on time, total, percentage, [clubs]]} """
    pattern = pattern.replace("_"," ")
    timeouts = services.compute_timeouts(pattern) # from services
    players={}
    for t in timeouts: # t = (match, {club_id:players})
        for c,pp in t[-1].items():
            for p in pp: players[p]=players.get(p,0)+1
    # to get total, we need to consider all matches
    for match in Match.objects.filter(competition__name__icontains=pattern):
        for team in (match.raw_data or {}).get('teams', {}).values():
            club_id = team['@id'].split('/')[-1]
            for p in team['players']:
                if data := players.get(p['username']):
                    if isinstance(data, int): data = players[p['username']] = [data, 0, []]
                    data[1] += 1
                    if club_id not in data[-1]: data[-1].append(club_id)
    players = { p:[s[0],s[1],100*s[0]/s[1],s[-1]] for p,s in sorted(
        players.items(), key= lambda t: (-t[1][0], t[1][1] ) )[:10] }
    return render(request, "tournoi/timeout.html", {'timeouts':timeouts, 'players':players, 'pattern': pattern})


### API FOR SCRAPING C.C FORUM/ANNOUNCEMENT PAGES ###
SECRET_TOKEN = "my-super-secret-token-88372"

# helper fct for bookmarklet_receiver
def french_to_aware_dt(french_date: str):
    try:
        # 1. Parse DD/MM/YYYY into a naive Python datetime (defaults to 00:00:00 time)
        if french_date:
            naive_dt = datetime.strptime(french_date, "%d/%m/%Y").replace(hour=12)
        # 2. Convert to a timezone-aware datetime (prevents Django RuntimeWarnings)
            return timezone.make_aware(naive_dt)
    except ValueError:
        # Fallback if the regex captured an invalid date like 32/13/2026
        pass


#helper fct for bookmarklet_receiver
def cc_response(data=None, status=404, **kwargs):
    if isinstance(data, str): data = {
        'success': True, 'message': data } if status<300 else {'error': data}
    response = JsonResponse(data, status=status, **kwargs)
    response["Access-Control-Allow-Origin"] = "https://www.chess.com"
    return response


@csrf_exempt
def bookmarklet_receiver(request):
    # 1. Handle the CORS Preflight request
    # Browsers send an 'OPTIONS' request first to check permissions
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "https://www.chess.com"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    # 2. Handle the actual data POST
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            token = data.get("token")
            # Security check
            if token != SECRET_TOKEN: return cc_response("Invalid token", status=403)

            # do the scraping in the JS, so let's expect a list of links
            if not(match_ids := data.get("match_ids")):
                return cc_response("No match id's found in HTML", status=404)

            url = data.get("url") # this is to identify the competition

            # Find the stub by the URL the user is currently on
            try:
                competition = Competition.objects.get(url=url)
            except Competition.DoesNotExist:
                return cc_response(f"No stub found for {url = !r}")#, status=404)

            update_fields = {'raw_data'} # currently we return before save() if no new "raw_data"

            # in case start_date and/or cutoff_date are already defined, DON'T
            # update these from the scraped data, which might be incorrect
            if not competition.start_date and ( # if date exists, do nothing
                start_date := french_to_aware_dt(data.get("start_date"))):  # e.g. "05/10/2026" for oct.2026
                    competition.start_date = start_date
                    update_fields |= {'start_date'}

            if not competition.cutoff_date and ( # if date exists, do nothing
                cutoff_date := french_to_aware_dt(data.get("cutoff_date"))):  # e.g. "05/10/2026" for oct.2026
                    competition.cutoff_date = cutoff_date
                    update_fields |= {'cutoff_date'}

            if not (raw_data := competition.raw_data or {}): competition.raw_data = raw_data

            if matches := raw_data.get('matches', []):
                ### merge with possibly existing & check whether new matches were added!
                if new_matches := set( match_ids ).difference( matches ):
                    matches . extend ( new_matches )
                else:
                    return cc_response(f"No new match id's found for existing {competition.name = !r}!")# status=404
            else:
                new_matches = raw_data['matches'] = match_ids

            # Save the extracted links into your JSONField
            competition.save(update_fields=update_fields)

            warnings = services.create_matches(new_matches, competition)
            message = "Competition {competition} non trouvée!" if warning is False\
                else f"Updated {competition.name} with {len(new_matches)} new matches!"

            if warnings:
                message += "\n⚠️ ATTENTION:\n" + "\n".join(warnings)
            return cc_response(message, 201)

        except json.JSONDecodeError:
            return cc_response("Invalid JSON format", status=400)
        except Exception as e:
            # Any unhandled crash gets caught here and sent safely back to JS
            return cc_response(f"Server error: {str(e)}", status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

#    path('create_match_data/', views.create_match_data, name='create_match_data'),
def create_match_data(request):
    # Récupère les compétitions "à créer" ou qui n'ont pas encore leurs matchs programmés
    competitions = Competition.objects.filter(status='to_create') # TODO : Ajuster ce filtre
    matches = []
    for comp in competitions:
        # Extraire les infos nécessaires depuis raw_data ou les champs du modèle
        matches.append({
            "titre": (name := comp.raw_data.get('title')),
            "description": comp.raw_data.get('description'),
            "club_hote_id": str(comp.raw_data.get('club_hote_id')),
            "club_invite_name": comp.raw_data.get('club_invite_name'),
            "date": comp.raw_data.get('date', '05/10/2026'),
            "days_per_move": str(comp.raw_data.get('days_per_move', '3')),
            "min_players": str(comp.raw_data.get('min_players', '3')),
            "max_players": str(comp.raw_data.get('max_players', '')),
            "min_rating": str(comp.raw_data.get('min_rating', '')),
            "max_rating": str(comp.raw_data.get('max_rating',
                '1400'if'1400'in name else'1000'if'1000'in name else'')),
            "games_per_player": "2",
            "min_games": "5" # nombre de parties un joueur doit déjà avoir jouées
        })
    response = JsonResponse(matches, safe=False)
    # Important : Autoriser la lecture cross-origin depuis Chess.com
    response["Access-Control-Allow-Origin"] = "*"
    return response

#    path('classement/<str:compet>/', views.classement, name='classement'),
def classement(request, compet: str):
    # This looks up the Competition where name matches the URL
    if "_" in compet: compet = compet.replace("_", " ")
    if competition := get_object_or_404(Competition, name=compet):
        classements = services.classement.calcul_classement(competition) # from tournoi.services
    return render(request, 'tournoi/classement.html', context = {
        'compet': competition or compet, 'classements': classements })

# path('clubs/', views.clubs, name='clubs'),
def clubs(request):
    clubs = Club.objects.order_by('name')
    return render(request, 'tournoi/clubs.html', {'clubs': clubs})

# path('maj_divers/', views.maj_divers, name='maj_divers'),
@staff_member_required
def maj_divers(request):
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

# OBSOLETE ?!
#path('update-match-names/', views.update_match_names, name='update_match_names'),
@login_required
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
          if match_ids := services.extract_match_ids_from_HTML(pasted_html): # defined in services.py
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
            if warnings := services.create_matches(match_ids, comp):
                messages.warning(request, "ATTENTION:" + "\n".join(warnings))
          else:
            messages.error(request, f"Impossible d'extraire la liste des rencontres.")# de l'URL {comp.url}
            match_ids=()
        else:
            messages.error(request, f"Pas de HTML reçu.")# de l'URL {comp.url}
        # Redirect back to the detail page so the user sees the new data
        return redirect('tournoi:comp-detail', compet=comp.name)

# OBSOLETE ?!
#single-match update view.
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
        if error := services.update_match(match):
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
        elif del_target := request.POST.get('del_compet'):
            if c := Competition.objects.filter(name=del_target).first():
                c.hidden = not c.hidden
                c.save(update_fields=['hidden'])
                messages.success(request, f"OK - compétition '{del_target}' modifiée en {c.hidden = }!")
            else: messages.error(request, f"Compétition '{del_target}' non trouvée!")

        # 3. terminer une compétition
        elif stop_compet := request.POST.get('stop_compet'):
            if matches := Match.objects.filter(competition__name=stop_compet):
                cnt = 0
                for m in matches:
                    if m.status != 'finished':
                        m.status = 'finished'; cnt += 1 ; m.save(update_fields=['status'])
                # now, cnt = number of affected records
                messages.success(request, f"OK - {cnt} rencontrés mis en 'terminée'")
                if c := Competition.objects.filter(name=stop_compet).update(status='finished'):
                    messages.success(request, f"OK - compétition {stop_compet} marquée 'terminée'")
            else: messages.error(request, f"Compétition '{stop_compet}' non trouvée!")

        # 4. Détails d'une compétition
        elif 'detail_compet' in request.POST:
            det_target = request.POST.get('detail_compet')
            comp = Competition.objects.filter(name=det_target).first()
            if comp:
                messages.info(request, f"Compétition '{comp.name}': URL={comp.url}")
            else:
                messages.error(request, f"La compétition '{det_target}' n'est plus dans la base!")

        # 5. Calculer le tableau
        #elif 'tableau' in request.POST: ...

        return redirect('tournoi:home'  # Redirect prevents double form submission on refresh!
            if not pattern else f"{reverse('tournoi:home')}{pattern}/")
    # GET Request: was a particular competition selected?
    if pattern: # or not request.user.is_staff and (pattern:=str(date.today().year)):
        # allow "sluggish" competition names
        for t in "-_":
            if t in pattern: pattern=pattern.replace(t," ")
        competitions = Competition.objects.filter(name__istartswith=pattern)
        if not competitions: return render(request, 'tournoi/simple_output.html', {
            'title': f'Aucune compétition dont le nom correspond au {pattern = !r}!'})
    else: return render(request, 'tournoi/simple_output.html', {
            'title': f'Bievenue dans la web app "Gestion CFE-CFT-LFR" &copy; 2025-2026 by MFH !',
            'output': """<p>Veuillez utiliser les liens dans la "barre de navigation" en haut de la page
            pour choisir la catégorie (CFE/LFR/CFT) des compétitions à afficher,
            ou les autres fonctionnalitées proposées.</p>
            Sinon, vous trouverez de plus amples informations concernant ces compétitions
            sur les forums maintenus par les organisateurs sur chess.com."""})
    # Prepare data for rendering
    matches_to_update = selected_compet = None
    if selected_name := request.session.get('compet'):
        if selected_compet := competitions.filter(name=selected_name).first():
            if request.user.is_staff:
                matches_to_update = list(selected_compet.matches.exclude(
                    status='finished').values_list('id', flat=True))
    header = {'title':"Gestion CFE-CFT-LFR"}
    if pattern := pattern.upper():
        match pattern:
            case "CFE": cat="Championnat de France par Equipe"
            case "LFR": cat="Ligue Française des Régions"
            case "CFT":
                cat="Coupe de France des Territoires"
                header['subtitle'] = """Remarque:
La première édition de la CFT, en 2023, s'appelait la <a href="/CVF">CVF : Coupe des Villes de France</a>."""
            case "CVF":
                cat="Coupe des Villes de France"
                header['subtitle'] = """Remarque:
Cette compétition n'a existé qu'en 2023, c'est ensuite devenu la <a href="/CFT">CFT : Coupe de France des Territoires</a>."""
            case _: cat = None
        if cat: header['title'] += f" (Catégorie {pattern} : {cat})"
    #elif request.user.is_staff:
    #    #header['subtitle'] =
    context = {
        'competitions': competitions, 'pattern': vars().get('pattern'), 'header':header,
        'selected_compet': selected_compet, 'matches_to_update':matches_to_update
    }
    return render(request, 'tournoi/cfe.html', context)
