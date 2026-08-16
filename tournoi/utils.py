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
'''
from tournoi.models import Club,Match
from django.db.models import F,Q # for top10
from tournoi.services import update_from_api

###### CLUBS #######

renames={
    "La Dame Noire": "Montigny-le-Bretonneux",
    "Le Plateau de Gergovie": "Clermont-Ferrand",
    "French Antilles": "Antilles Françaises",
    "CHAMBERY SAVOIE ECHECS": "Chambéry",
    "La Tour Infernale": "Isbergues",
}
all_clubs = Club.objects.all()

def get_club(name): # avoid "crash" if name is duplicate or nonexistant
    # returns None if nonexistant
    return Club.objects.filter(name=name).first()

def do_rename_clubs():
    for c in all_clubs:
        if not(name := c.name): continue
        if name.startswith("Team"): name = name[5:] # this and next may both apply
        if name.endswith("Metropole"): name = name[:-10]
        elif name.startswith("K6 "): c.name = "Cassis"
        elif name.startswith("Fédération "): c.name = "Tahiti"
        elif name.lower().endswith("checs"): # échecs ; Echecs ; ECHECS ; ...
            name = c.name[:-7].strip()
        elif name.endswith("Massilia"): c.name = "Marseille"
        elif name.endswith("Equipa Tolosa"): c.name = "Toulouse"
        elif name in renames: name = renames[name]
        elif name == c.name: continue
        print(f"renaming '{c.name}' =>", name := name.strip(" -"))
        c.name = name
        c.save()
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
