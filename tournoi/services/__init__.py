""" tournoi/services/__init__.py - (c) 2026 by MFH

    In course of migration from services.py to services/xxx.py
"""
import re, requests

from tournoi.models import Competition,Match,Club


### re-imports for .views :

from tournoi.constants import aliases, headers # used below in compute_multiteam() ; also in .classement

# TODO : check whether "Classement" is needed in views
from .classement import calcul_classement, Classement #, TD
from .extract import create_matches, extract_match_ids_from_HTML


# called from views.api_next_match
def get_next_match(comp: Competition):
    """Renvoit la Json Response avec les données nécessaires pour remplir le
    formulaire de création de match sur chess.com, pour le prochain match à
    créer dans la ou les `compet`."""
    try:
        create = comp.raw_data['create'] # must be present
        if not (rounds := create.get('rounds')):
            rounds = [create]
        # to get a parameter, first check in `ronde`, then in `create`
        get = lambda key, default='': ronde.get(key, create.get(key, default) if create != ronde else default)
        for ronde in rounds:
            # For 'pairings', no need to check both, because if 'create' has 'pairings',
            # it can't have rounds, so `ronde` = `create`.
            if not (pairings := ronde.get('pairings')):
                # créer les appariements pour une poule. round['teams'] doit être défini
                import itertools
                pairings = itertools.combinations(round['teams'], 2)
            for pair in pairings:
                clubs = Club.objects.in_bulk(pair)
                team1, team2 = (clubs.get(team) for team in pair)
                title = get('title', comp.name)
                if " vs " not in title:
                    title = title.trim(" :") + " : {team1} vs {team2}"
                title = title.format(team1=team1, team2=team2)
                if Match.objects.filter(name=title): continue # this match was already created
                data = {
    "titre":        title, # str(.)
    "description":  get('description', "Rencontre de la compétition "+comp.name), #TODO : add "cut-off ..."
    "club_hote_id":     team1.club_id,
    "club_invite_name": team2.raw_data.get('name', team2.name),
    "date":             get('start_date', comp.start_date), # format: DD/MM/YYYY
    "days_per_move":    get('days_per_move', "3"),
    "min_players":      get('min_players', "3"),
    "max_players":      get('max_players', ''),
    "min_rating":       get('min_rating', ''),
    "max_rating":       get('max_rating', '1400'if'1400'in title else'1000'if'1000'in title else''),
    "games_per_player": "2",
    "min_games":        "5" # nombre de parties un joueur doit déjà avoir jouées pour pouvoir s'"inscrire
                }
                return data
                matches . append( data )
                break # for the moment, we send back one single match
            else: continue # no break occurred : go to next round
            break # don't go to next round
        # the loop is done (for this competition)
    except: return # empty => main loop in the view goes on
    return matches # api_next_match in views will wrap it in a JsonResponse(


def compute_timeouts(pattern):
    """Return a list[ (match, timeouts) ] for the competitions whose name matches
    `pattern`, where timeouts is a dict {club_id: [player_id's...]}."""
    timeouts = []
    for match in Match.objects.filter(competition__name__icontains=pattern):
        if (d := match.raw_data) or match.update_from_api() and (d := match.raw_data):
            if d['status']=='registration': continue # consider only finished & ongoing
            if (t := d.get('timeouts')) is None:
                t = {} # make a dict for this match
                for team in d.get('teams', {}).values():
                    for p in team.get('players',()):
                        if 'timeout'in p.values():
                            if (club_id := team['@id'].split('/')[-1]) not in t: t[club_id]=[]
                            t[club_id].append(p['username'])
                d['timeouts'] = t
                if d['status'] == 'finished':
                    match.status = 'finished'
                    match.save()
            if t: timeouts.append( (match, t) )
    return timeouts


def compute_multiteam(pattern=''):
    """Faire la liste des joueurs multi-équipe."""
    multi_team_players=[] ; club_prefix = "https://www.chess.com/club/"
    ALIASES = { club_prefix+a: club_prefix+b for a,b in aliases.items() }
    players = {} ; match_count = 0
    for match in Match.objects.filter(competition__name__icontains=pattern):
        match_count += 1
        if (d := match.raw_data) or match.update_from_api() and (d := match.raw_data):
            for team in d.get('teams',{}).values():
                if (URL := team['url'])in ALIASES:
                    URL = ALIASES.get(URL) ; CLUB_NAME = ''
                else: CLUB_NAME = team['name']
                #team_id = URL, team['name']
                for player in team.get('players',()):
                    if player_teams := players.get( name := player['username'] ):
                        if this_team := player_teams.get( URL ):
                            this_team .append( match )
                        else:
                            this_team = player_teams[ URL ] = [ match ]
                            if len(player_teams)==2: multi_team_players.append( name )
                    else: players[name] = { URL: (this_team := [match]) }
                    if CLUB_NAME and not isinstance(this_team[0], str):
                        this_team.insert(0, CLUB_NAME)
    return [ MTP( player, players[player] ) for player in multi_team_players ]

from typing import NamedTuple
class MTP(NamedTuple):
    player: str; teams: dict
    def __str__(self):
        output = [f'<dt><a href="https://www.chess.com/member/{self.player}">{self.player}</a>:']
        for club_url, matches in self.teams.items():
            club_name = matches.pop(0) if isinstance(matches[0], str) else club_url.split('/')[-1]
            output.append( f'<dd><a href="{club_url}">{club_name}</a>:' )
            output.append( ', '.join(m.linkedname()for m in matches) )
        return'\n'.join(output)


def update_match(match: Match):
    """Fetches data from Chess.com API and updates the Match object.
    Returns 'None' on success (also if nothing to update), else an error message (str | Exception).
    """
    if update := match.update_from_api(): # this updates only raw_data
        # returns False if the API data hasn't changed: then no need for any updates
        # (except "last updated" timestamp, not yet implemented)
        if update is not True: return update # error message
        # Match.raw_data is now complete & up to date
        api_data = match.raw_data; update_fields = []
        if match.num_boards != api_data["boards"]: # was "registration" status ?!
            match.num_boards = api_data["boards"]
            update_fields . append( "num_boards" )
        if not match.status or match.status == 'unknown': # never initialized
            # initialize the club names
            for key, team in api_data["teams"].items():
                # key = 'team1' or 'team2'.
                # Corresponding `team` is a mini `Club` + player list
                if not getattr(match, team_id := key+'_id'): # just the id, avoid loading Club from DB
                    club_id = team["@id"].split('/')[-1]
                    defaults = {'raw_data': { k:team[k] for k in('name',) }}
                    # '@id' == Club.api & 'url' = Club.url shouldn't be useful
                    Club.objects.get_or_create(id=club_id, defaults=defaults)
                    # Club.save() will compute .name and .abbreviation from .raw_data
                    setattr(match, team_id, club_id)
                    update_fields . append( team_id )
        # if club names are already initialized, update scores
        for key, team in api_data["teams"].items():
            if getattr(match, attr := "score_"+key) != team["score"]:
                setattr(match, attr, team["score"]) ; update_fields += [attr]
            if match.status != api_data['status']:
                match.status = api_data['status']; update_fields += ["status"]
            match.save(update_fields=update_fields) # and return None

