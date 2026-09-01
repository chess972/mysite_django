'''
    tournoi/utils.py - (c) 2026 by MFH
    Usage:
        python manage.py shell
        from tournoi.utils import *

    last update: 5.8.2026
    ADMIN SNIPPETS :
    - define all_clubs, all_matches
    - do_rename_clubs(), name_matches(), get_club(name), ...
    - update_club_abbrevs() : if club hasn't abbrev yet, add one

Remark:
    initially created as tournoi/management/commands/admin_snippets.py
    for use as `python manage.py admin_snippets`
    but this requires defining
    class Command(BaseCommand):
        handle(self, *args, **options): ...

Exemple de création de match "manquants":
data={"matches": ["1641631", "1641711", "1641657", "1641639"]}
from tournoi.models import *
comp = Competition.objects.filter(name="LFR 2024 Quarts de finale").first()
from tournoi.services import create_matches
create_matches(["1641657", "1641639"], comp)
=> ["Match '01641657' en double - informez un admin!"] # match compte aussi en CFE R8


Autre exemple de création de match manquants : la liste suivante s'est affichée, mais actualisation impossible,
peut-être en raison d'un club inexsitant (team-grand-est-1 : renommé en ...? ).
m =  """1309963^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1312625^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1314527^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1327097^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1330063^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1344361^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1338495^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1363771^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1353805^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1364835^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0
   ...: 1365917^I^I? team 1 ?^I? team 2 ?^I0,0 - 0,0^I0""".splitlines()
m=[m.split("?")[0].strip()for m in m]
m # Out[3]: ['1309963', '1312625', '1314527', '1327097', '1330063', '1344361', '1338495', '1363771', '1353805', '1364835', '1365917']

from tournoi.models import *
from tournoi.services import update_match
mm = Match.objects.filter(id__in=m)
len(mm) #   Out[7]: 11

for ma in mm: print(update_match(ma))
'NoneType' object has no attribute 'get' ... (11 times) ; also the error shown in messages

for ma in mm:
     if not ma.raw_data: ma.raw_data={}
     print(update_match(ma))            # ==> True : now OK !


'''
from tournoi.models import Competition,Club,Match
from django.db.models import F,Q # for top10
from tournoi.services import update_from_api

###### CLUBS #######

renames={
    "La Dame Noire": "Montigny-le-Bretonneux",
    "Le Plateau de Gergovie": "Clermont-Ferrand",
    "French Antilles": "Antilles Françaises",   # AFTER stripping off "Team" !
    "CHAMBERY SAVOIE ECHECS": "Chambéry",       # BEFORE stripping off "ECHECS" !
    "La Tour Infernale": "Isbergues",
}
all_clubs = Club.objects.all()

def get_club(name): # avoid "crash" if name is duplicate or nonexistant
    # returns None if nonexistant
    return Club.objects.filter(name=name).first()

def do_rename_clubs():
    for c in all_clubs:
        if not(name := c.name): continue
        if name.startswith("Team"): name = name[5:].strip("- ") # this and later "endswith" may both apply

        if name.endswith("Metropole"): name = name[:-10].strip("- ")
        elif name.endswith("Massilia"): name = "Marseille"
        elif name.endswith("Equipa Tolosa"): name = "Toulouse"
        elif name.startswith("Fédération "): name = "Tahiti"
        elif name.startswith("K6 "): name = "Cassis"
        elif name in renames: name = renames[name]

        if name.lower().endswith("checs"): name = c.name[:-7] # échecs ; Echecs ; ECHECS ; ...
        elif name == c.name: continue # the first 'if' may have changed it

        print(f"renaming '{c.name}' =>", name := name.strip("- "))
        c.name = name
        c.save(update_fields=['name'])
'''
    for k,v in renames.items():
        try: c=all_clubs.get(name=k); c.name=v; c.save()
        except Exception as e: print(f"Skipped {k,v}: {e}")
'''

def update_club_abbrevs():
    print(end="Updating names... "); do_rename_clubs()
    print("Updating abbreviations...: ")
    updated_count = 0
    for club in Club.objects.filter(Q(abbreviation__isnull=True) | Q(abbreviation='')):
        if not club.name:
            if not club.raw_data:
                print(end="Fetching data for {match.id = } from API...")
                if update_from_api(club) is not True: continue
            if not(name := club.raw_data.get('name')): continue
            while name: club.name = name; name=(
                        club.name[5:] if club.name.lower().startswith("team")
                else    club.name[:-7] if club.name.lower().endswith("checs") # échecs, Echecs...
                else    club.name[:-10] if club.name.lower().endswith("metropole")
                else '')
            club.save(update_fields=['name']) ; print(f"updated club {club.id}'s name to {club.name}")
        club.abbreviation = club.name[:3].upper()
        club.save(update_fields=['abbreviation'])
        print(f"{club.abbreviation} : {club.name}")
        updated_count += 1
    print(f"OK - {updated_count} abbréviations initialisées!"if updated_count
            else"Rien à actualiser!")


def update_club_ids():
    print("Updating numerical club id's... ")
    updated_count = 0
    for club in Club.objects.filter(raw_data__club_id__isnull=True):
        if not club.raw_data:
            print(end = f"Fetching data for {club.id = } from API...")
            if update_from_api(club) is not True:  # no update available
                ...
        club.save(update_fields=['name'])
        print(f"updated club {club.id}'s name to {club.name}")
        print(f"{club.abbreviation} : {club.name}")
        updated_count += 1
    print(f"OK - {updated_count} abbréviations initialisées!"if updated_count
            else"Rien à actualiser!")


###### MATCHES #######

all_matches = Match.objects.all()
def name_matches():
    """If match.name is not defined (None or ''), retrieve it from the raw_data."""
    updated_count=0 ; unknown=[]
    for m in all_matches:
        if not m.name:
            if m.raw_data and 'name' in m.raw_data:
                m.name = m.raw_data['name']
                m.save(update_fields=['name']) ; print(f"updated match {m.id}'s name to {m.name}")
                updated_count += 1
            else: unknown += [m.id]
    print("Done - number of updates:",updated_count)
    if unknown:
        print("The following matches don't have a name, nor (API) raw_data:",unknown)
