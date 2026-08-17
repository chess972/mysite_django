# tournoi/services.py
from .models import Match,Club  # Import your models here if the scraper needs to save directly
import re, requests

aliases = { 'normandie': 'echiquier-de-normandie',
            'paris-neuf-trois': 'saint-denis-93-chess',
        }

headers = {'User-Agent': 'CFE_LFR_CFT_Tournament_management_App (contact: echecs972@gmail.com)'}

def update_from_api(item):
    """Forks item (Club | Match), update the raw_data field from the api.chess.com, if necessary.
    Returns True if updated, False if not, str or exception on failure."""
    try: # fetch data from api.chess.com
        response = requests.get(item.api, headers=headers)
        if response.status_code != 200: return "Failed to connect to API"
        api_data = response.json()
        if item.raw_data != api_data:
            item.raw_data = api_data ; item.save(update_fields=['raw_data'])
            return True
        return False
    except Exception as e: return e

def update_match(match):
    """Fetches data from Chess.com API and updates the Match object.
    Returns 'None' on success, else an error message (str | Exception).
    """
    if update := update_from_api(match):
        # returns False if the API data hasn't changed: then no need for any updates
        # (except "last updated" timestamp, not yet implemented)
        if update is not True: return update # error message
        api_data = match.raw_data; update_fields = []
        if match.num_boards != api_data["boards"]: # was "registration" status ?!
            match.num_boards = api_data["boards"] ; update_fields += ["num_boards"]
        if not match.status or match.status == 'unknown': # never initialized
            # initialize the club names
            for key, team in api_data["teams"].items():
                if not getattr(match, key):
                    club_id = team["@id"].split('/')[-1]
                    Club.objects.get_or_create(id=club_id, defaults={
                        'name': team["name"], 'abbreviation': team["name"][:3].upper()})
                    setattr(match, k := key+"_id", club_id)
                    update_fields += [k]
        # if club names are already initialized, update scores
        for key, team in api_data["teams"].items():
            if getattr(match, attr := "score_"+key) != team["score"]:
                setattr(match, attr, team["score"]) ; update_fields += [attr]
            if match.status != api_data['status']:
                match.status = api_data['status']; update_fields += ["status"]
            match.save(update_fields=update_fields) # and return None

class TD(str):
    def __new__(c, text, cls='', link=''):
        s = super().__new__(c, text); s.cls=cls ; s.link=link; return s
    def __str__(self): return self.classify(f' class="{self.cls}"'if self.cls else'')
    def classify(self, c): return f"<td{c}>{self.linkify(str.__str__(self))}</td>"
    def linkify(self, s): return f'<a href="{self.link}">{s}</a>' if self.link else s

class Classement(dict):
    """La structure classement calcule tout ce qu'il faut pour afficher
    (avec str => rendu HTML) un tableau de classement de la forme:
    n°   Club        ABBR.1   ...   ABBR.N   F Pts V D N SB MA
    k club[k].name score[k].1 ... score[k].N ...
    où score[k].j = (gagnés, perdues[, restant]), F = finis (résultat connu),
    Pts = 2V+N ; V = victoires, D = défaites, N = nulles (en terme de rencontres),
    SB = Sonneborn-Berger (points des adversaires vaincus + (non perdues) x 0.5),
    MA = 'match average" = nombre de *parties*(!) gagnées - perdues.
    Le numéro k=1,...,N étant calculé l'ordre (décroissant) de (Pts, SB, MA).

    Typiquement, la structure est initialisée en donnant les match_ids,
    éventuellement un `title` = sous-titre (en cas de plusieurs groupes),
    à partir de quoi elle calcule les entrées 'matches' (rappatriés de la BDD),
    'scores' = {club_id: {opp_id: (games won, lost, remain, match_id) where
                match['teams'] == {club_id, opp_id}} for match in self.matches},
    'results' = {club_id: {'scores':scores[club_id], 'F':..., 'Pts': ..., ...}},
    'classement' = {club_id: club} dans l'odre du classement,
    'groupes' = [[*club_ids du groupe] pour groupe = {clubs qui se sont affrontés}],
    'classements' = [Classement(groupe g), g = 1 .. G=#groupes] = [self] si G = 1,
    'headers' = ['n°', 'Club', ABBR.1 ... ABBR.N, 'F', 'Pts', ...],
    'rows' = generateur de [TD[k,1], ... TD[k,N]] for k = 1,..., N=#classement,
    où TD est une sous-classe de str qui peut avoir attributs .cls et/ou .link.

    La structure est un dict dont les entrées peuvent être obtenues aussi comme
    attribut, et sont calculées si pas encore présents:
        self.xxx = self['xxx'] = self.get('xxx', self.compute_xxx()).
    """
    def __getattr__(self, key): # called (only) if the attribute doesn't exist
        if key not in self: # compute & store it
            if key.startswith(c := "compute_"): return # avoid infinite recursion
            self[key] = getattr(self, c+key)()
        return self[key]
    __missing__ = __getattr__ # idem, if an entry doesn't exist

    def __init__(self, *args, **kwargs):
        if len(args)==1: # make a copy, if the only arg is a dict or type(self)
            if isinstance(args[0], dict): self |= args[0] | kwargs; return
        self.match_ids=args if len(args)!=1 or isinstance(args[0], str|int
                    ) else args[0] if isinstance(args[0], tuple
                    ) else tuple(args[0]) #  list or generator (or... ?)
        self |= kwargs

    def __str__(self): return f"""{self.style}
{f"<h2>{self.title}</h2>\n"if self.get('title') else''}{self.get('comment','')}
<table border=1 cellspacing=0>
<thead><tr><th>{'</th><th>'.join(self.headers)}</th></tr></thead>
<tbody><tr>{'</tr>\n<tr>'.join(''.join(str(td)for td in r)for r in self.rows)}</tr>
</tbody></table>{self.explication}
{self.footnote}"""

    style="""<style>th {min-width: 2em} td {text-align:center; padding: 3pt}
.self {background: black} .penalty {background: salmon} .unkn {background: orange}
.won {background: lightgreen} .lost {background: #ffbbbb} .draw {background: lightyellow}
</style>""" # can be set to '' if additional tables are displayed on the same pages

    # If there is a unique group, there should be no (sub)'title'.
    # If there are several groups, they use title = titles[i], i = 0 .. len(groups)-1,
    #  where the list 'titles' can be given, or it is computed as follows:
    def compute_titles(self):
        if not (title := self.get('title', "Groupe ")).endswith(' '): title += " "
        return [f"{title}{n+1}"for n in range(len(self.groups))]

    # The headers have a colum with its abbreviation for each club in self.classement
    # Therefore, if a compet is split in several groups => classements, make sure it
    # doesn't have an obsolete 'headers' entry corresponding to *all* clubs of compet.
    def compute_headers(self): return ["n°", "Club", *(club.abbreviation for club
            in self.classement.values()), 'F', 'Pts', 'V', 'D', 'N', 'SB', 'MA']

    @property # this is (almost?) the only attribute that is not stored as dict entry
    def rows(self):
        """This `yield`s the rows of the competition table, as list of TD elements."""
        h = self.headers ; r = self.results ; c = self.classement
        # Get the `cls` for a given score entry
        cls=lambda s: ('penalty'if s[0]<0 else 'unkn' if 0 < s[2] >= abs(s[0]-s[1])
                else 'won'if s[0] > s[1] else 'lost' if s[0] < s[1] else 'draw')
        for no,(club_id,club) in enumerate(c.items(), 1):
            rr = r[club_id]; yield [TD(no), TD(club.name, link=club.url),
                    *(TD(s[:3 if s[2]else 2], link=s[-1].url, cls=cls(s))
                      if(s := rr['scores'].get(opp)) else
                      TD('-',cls='self' if opp==club_id else None) for opp in c),
                    *(TD(rr[k]) for k in h[-7:]) ] # 'F', 'Pts', ...

    @property
    def explication(self):
        if len(self.classement) < 3: return ''
        draw = ', <span class="draw">jaune pour nulle</span>'if any( s[0]-s[1] == 0 == s[2]
            for c in self.classement for s in self.scores[c].values() )else ''
        unkn = ', <span class="unkn">orange = encore indécis</span>'if any(0 < s[2] >= abs(s[0]-s[1])
            for c in self.classement for s in self.scores[c].values() )else ''
        return f"""<p>Rappel: Le classement s'effectue par
<b>P</b><small>oin</small><b>ts</b> (= 2&#8239;&times;&#8239;<b>V</b><small>ictoires</small> +
1&#8239;&times;&#8239;<b>N</b><small>ulles</small> + 0&#8239;&times;&#8239;<b>D</b><small>éfaites</small>),
puis par <a href="https://fr.wikipedia.org/wiki/Syst%C3%A8me_Sonneborn-Berger"
><b>S</b><small>onneborn</small>-<b>B</b><small>erger (cf. Wikipedia)</small></a>,
et enfin par <br/> &laquo;&#8239;<b>M</b><small>atch</small>-<b>A</b><small>verage</small>&#8239;&raquo;
(parties gagnées - parties perdues). Les résultats des rencontres sont de la forme (g, p) ou (g, p, r),
où g/p/r = parties <br/> gagnées/perdues/restantes, <span class="won">fond vert pour rencontre gagnée</span>,
<span class="lost">fond rose pour rencontre perdue</span>{draw}{unkn}.</p>
"""
    footnote_cancelled = """<p><b>N.B.:</b>
Un <span class="penalty">score négatif sur fond "saumon"</span> signifie que l'équipe qui n'a pas fourni<br/>
assez de joueurs s'est vu attribuer une pénalité pour la rencontre annulée.</p>"""
    @property
    def footnote(self): return self.footnote_cancelled if any(s[0] < 0
        for c in self.classement for s in self.scores.get(c,()).values()) else ''

    def compute_classements(self):
        """Etablir la liste des classements, s'il y a plusieurs groupes (sinon,
        classements = [self]). Chaque classement aura un 'title', pris dans liste
        self.titres (calulée si elle n'existe pas) qui sera affiché comme (sous)-titre.
        """
        if len(groups := self.groups) > 1:
            classements = []
            for no_grp, grp in enumerate(groups):
                title = self.titles[no_grp]
                classements += [c := Classement(self, title=title)] # make a copy
                # in the copy, we keep the computed scores, results, ...
                c['classement'] = {cid:club for cid,club in self.classement.items() if cid in grp}
                # say: "only one group"
                c['groups'] = [grp]; c.pop('headers', None) # must be recomputed (with less columns)!
            return classements
        return [self]

    def compute_groups(self):
        "Utilise self.scores. Renvoit une liste de listes de club_id's."
        groups = {}
        for club_id,sc in self.scores.items():
                if g := groups.get(club_id):
                    for c in sc:
                        if c not in g: g += [c]; groups[c] = g
                else: g = [club_id, *sc];  groups |= {c:g for c in g}
        return [g for c,g in groups.items() if c==g[0]]

    def compute_matches(self):
        "self.matches = liste (QuerySet) de tous les Match avec id in match_ids."
        return Match.objects.filter(id__in=self.match_ids)

    penalty_not_enough_players = -3 # val.par défaut pour pénalité si annulation cause nbre insuff. de joueurs

    def compute_clubs(self):
        "Return a dict { club_id: club } for all participating clubs."
        club_ids = list(self.results)
        return {club.id:club for club in Club.objects.filter(id__in = club_ids)}

    def compute_classement(self):
        """Return dict { club_id: club } ordered by result. This may be [later reduced to]
a subset of (all) `self.clubs` belonging to a (sub)group (poule, finale...),
which compute against each other."""
        clubs = self.clubs
        return {club_id: clubs[club_id] for club_id,s in
                sorted(self.results.items(), reverse=True, key=lambda cs:
                            (cs[1]['Pts'],cs[1]['SB'],cs[1]['MA'],-cs[1]['F']))}

    def compute_scores(self):
        """Renvoit un dict {club_id: scores} où scores = {club2_id: (won,lost,remain,match)} }}.
        Utilise seulement self.match (les vrai "Match"), mais sinon rien d'autre.
        Applique aussi les `alias` (global dict), le cas échéant (=> peut enlever des club_id).
        """
        scores = {}; rnd = lambda s: int(s)if s.is_integer()else s
        for m in self.matches:
            if not m.raw_data: self['unknown']=1; continue # match needs to be updated !
            teams = m.raw_data.get("teams") #("team1", "team2")
            club_ids = [getattr(m, t+"_id") for t in teams]
            score = [rnd(getattr(m, "score_"+t)) for t in teams]
            if cancelled := not any(score) and m.status=="finished":
                self['cancelled'] = True
                min_players = m.raw_data.get('settings',{}).get('min_team_players',3)
                for i,t in enumerate(teams.values()):
                    if len(t['players']) < min_players:
                        score[i] = self.penalty_not_enough_players
            for i,cid in enumerate(club_ids):
                if cid not in scores: scores[cid] = {}
                scores[cid][club_ids[1-i]] = (score[i], score[1-i], m.remaining, m)
                # not(0 < m.remaining >= abs(s[0]-s[1])) : known -- not really useful

        # merge aliases if relevant ## uses global dict `aliases`
        # note : this may remove a club that is in clubs from the dict!
        if'aliases'in globals():
            for old, new in aliases.items():
                if old not in scores: continue # if not in keys, then also not in values
                if new in scores: # also played under the new id
                     scores[new] |= scores.pop(old) # merge
                else: scores[new] = scores.pop(old) # just "rename the key"
                for sc in scores.values():
                    if old in sc: sc[new] = sc.pop(old)
        return scores

    def compute_results(self):
        """Renvoit un dict {club_id: {'Pts':...,'MA':..., 'scores': scores[club_id]}.
        Utilise seulement self.scores, rien d'autre."""
        results = {} # compute points etc. based on scores
        for club_id, scores in self.scores.items():
            known = {c:s for c,s in scores.items() if not 0 < s[2] >= abs(s[0]-s[1])}
            ss = list(known.values())
            result = results[club_id] = {
                'F': len(ss),
                'V': sum(s[0]>s[1] for s in ss),
                'D': sum(s[0]<s[1] for s in ss),
                'N': sum(s[0]==s[1] for s in ss),
                'MA': sum(s[0]-s[1] for s in scores.values() if s[0] >= 0 <= s[1]),
                'SB': { c: (1 if s[0] > s[1] else 0.5)
                        for c,s in known.items() if s[0]>=s[1]}, # first step: list defeated clubs
                'scores': scores}
            result['Pts'] = 2*result['V'] + result['N'] + sum(
                                s[0]<0 for s in ss)*self.penalty_not_enough_players
            # now that [Pts] is defined for all clubs, we can compute SB
        for club_id, result in results.items():
            result['SB'] = sum(max(results[c]['Pts'],0)*coeff for c,coeff in result['SB'].items())
        return results

    # For repr, we keep only the match id's which allows to re"construct"/compute everything
    # except the title (=> add `title=...` if custom title is given).
    # But repr isn't really used in the web app, since it can't be 'JSON-serialized'.
    # To store it in JsonField raw_data, we store just the list of match id's,
    # or dict {'match_ids':..., 'title':...} if title is given.
    def __repr__(self): return f"""{type(self).__name__}({','.join(self.match_ids
        )}{f',title={self.title!r}' if self.get('title') else ''})"""
#class Classement

def calcul_classement(compet:str):
    """Return a dict corresponding to the 'classement' table(s).
    As of now, this function returns a list[Classement] ; rationale:
    many competitions fall apart into independent groups.
    Each Classement has entries and methods:
    headers = ['#', 'Club', ABBR.1,...,ABBR.N, 'F', 'Pts', 'V', 'D', 'N', 'MA', 'SB']
    classement = { club_id: club } ordered by result
    result = { club_id: scores } where scores = { opponent_id: (wins,loss,remain,match) }
    rows = (row.k for k = 1, ..., len(clubs)) in order of ranking
        row.k: [k, club, score.k.vs.1,...,score.k.vs.N, F.k, ... ]
    """
    if isinstance(compet, str): # shouldn't happen - already fetched from DB in views
        compet = get_object_or_404(Competition, name=compet)
    if not compet: return[f"Compétition inconnue ou non trouvée."]
    if not(data := compet.raw_data): data = compet.raw_data = {}

    # (liste des) classements déjà connue: renvoyer.
    # (Ils seront recalculés quand même.)
    # Dans (raw_)data, les classements sont des listes de match_id,
    # ou des dicts avec une entrée match_ids et une entrée "title".
    if classements := data.get('classements'):
        return [Classement(c)for c in classements]

    # sinon, voir si la liste des match est déjà stockée
    if not(matches := data.get('matches')):
        if matches := [m.id for m in Match.objects.filter(competition=compet)]:
            data['matches'] = matches ; compet.save(update_fields = ['raw_data'])
        else:
            return[f"Définition de la compétition {compet!r} incomplète - Le classement ne peut être établi !"]
    # sinon, voir si des groupes sont spécifiés.
    # Les groupes peuvent être des listes de match_id,
    # ou des dict avec typiquement une entrée "match_ids" et une entrée "title".
    classement = Classement(*matches)
    if t := data.get('titles'): classement['titles'] = t # titles are given
    elif t := data.get('title'): classement['title'] = t # titles will be computed from "title"
    # this innocent line creates the list of all "classements" !
    if len(c := classement.classements) > 1:
        # data['classements'] = ; compet.save(update_fields=['raw_data'])
        if o := data.get("order"): # reorder
            c = classement['classements'] = [c[j] for j in o]
        # now "partition" the match_ids and save the "split" classements in the database.
        data['classements'] = [{'title': cl.title, 'match_ids':
                list({ s[-1].id for club_id in cl.classement
                                for s in cl.scores[club_id].values()}),
            } for cl in c]
        if data.get('save'):
            compet.save(update_fields=['raw_data'])
    return c
'''
"classements": [{"title": "D1 top final", "match_ids": ["s", "a", "i", "m"]},
{"title": "play off D1/D2", "match_ids": ["s", "e"]},
{"title": "play off D1/D2", "match_ids": ["s", "e", "x"]},
{"title": "play off D2/D3", "match_ids": ["1", "s", "n"]},
{"title": "play off D2/D3", "match_ids": ["s", "e", "r"]},
{"title": "D3", "match_ids": ["1", "g", "o", "e"]}]
'''

def extract_match_ids_from_HTML(HTML, pattern = "/club/matches/"):
    match_ids = [dd := {'len_HTML': len(HTML), 'num_off':0}] ; cutoff_date = dd
    match_regex = re.compile(f'href=["\']https?://www[.]chess[.]com{pattern}([^"\']+)["\']', re.I)
    cutoff_regex = re.compile(r'cut+[ -]off.+le\s+(\d{2}/\d{2}/20\d{2})', re.I) # IGNORECASE
    stop_pattern = 'id="social-share"'
    if isinstance(HTML, str):
        # dd['<'] = HTML.count('<') ; dd['>'] = HTML.count('>')
        HTML = HTML.replace("</p>","\n").replace("</div>","\n").replace("<br","\n<br").splitlines()
        dd['num_lines'] = len(HTML)
    for line in HTML:
        if pattern in line:
            for m_id in match_regex.findall(line):
                match_ids . append( (m_id.split("/")[-1] if '/' in m_id # remove club name if it was 'inserted'
                                else m_id).split("?")[0]) # remove query string if present
        elif 'off' in line:
            dd['num_off'] += 1
            for m in cutoff_regex.findall(line):
                cutoff_date[m] = cutoff_date.get(m, 0) + 1
        elif match_ids and stop_pattern in line: break
    return match_ids


def extract_match_ids_from_web(url, pattern = "/club/matches/"):
    """
    Scrapes the chess.com forum URL and returns a list of match IDs.
    Example URLs : (NOTE: THE PAGE MUST BE PUBLICLY AVAILABLE !)
    https://www.chess.com/fr/clubs/forum/view/cfe2026-d1
    https://www.chess.com/fr/clubs/forum/view/lfr2026-l1
    https://www.chess.com/fr/announcements/view/calendrier-lfr2025-en-moins-de-1400
    https://www.chess.com/fr/announcements/view/cft2026-r4
    NOTE: the HTML code with match-urls can be of the form :
    X vs Y: <a href="https://www.chess.com/club/matches/1869975" target="_blank">R&eacute;sultat</a><br />
    or:
    Boulogne - Bordeaux <strong><a href="https://www.chess.com/club/matches/bordeaux/1870055">Résultat</a>

    This function will strip the club name, if present, and return only the 'basename' part.

    Possible stop patterns: [We use the first one. TODO: double-check: present in older posts?]
    id="social-share" *** very good *** in Forum & Announcement, we use this.
    <div class="cc-section"> *** OK, in both Forum & Announcement, but also BEFORE the data.
    <div class="post-category-link-component"> *** very good ***, in both
      data-cy="section-link"
      class="post-category-link-category "
    <footer id="navigation-footer" class="navigation-footer-component navigation-footer-hide"> *** good but late ***
    """
    # NOTE: We expect pattern to include a leanding & a trailing '/'
    match_regex = re.compile(f'href=["\']https?://www[.]chess[.]com{pattern}([^"\']]+)["\']', re.I)
    cutoff_regex = re.compile(r'cut+[ -]off.+le\s+(\d{2}/\d{2}/20\d{2})', re.I) # IGNORECASE
    stop_pattern = [ 'id="social-share"', # 'chesscomfiles.com/uploads/' : also before data
                     '<footer ' ]

    response = requests.get(url, headers=headers, stream=True)
    if not response.ok:
       return f"Problem retrieving page '{url}': {response.status}"

    match_ids = [] ; cutoff_date = {}

    binary_pattern = bytes(pattern)
    binary_cutoff = bytes("t-off")
    binary_stop_pattern = [ bytes(p) for p in stop_pattern ]

    # Now we will scan through the lines of the HTML page (often quite messy !!)
    # change `pattern` to a list, last item being "stopping patterns"

    for bline in response.iter_lines(): # Original page is in binary.
        # We search the binary for efficiency,
        # and we decode a line only when it has the pattern
        if binary_pattern in bline:
            for m_id in regex.findall(bline.decode()):
                match_ids . append(m_id.split("/")[-1] if '/' in m_id else m_id)
        elif binary_cutoff in bline:
            if m := cutoff_regex.search(bline.decode()):
                if m.group(1) in cutoff_date: cutoff_date[m.group(1)] += 1
                else: cutoff_date[m.group(1)] = 1
        elif match_ids and any( p in bline for p in binary_pattern ): break

    if cutoff_date: match_ids.append(cutoff_date)
    return match_ids
