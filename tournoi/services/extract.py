""" tournoi/services/extract.py  - (c) 2026 by MFH

    Functions related to the extraction of data from web pages:

    - create_matches() :  used by views.bookmarklet_receiver() and views.extract_matches()
    - extract_match_ids_from_HTML()
"""
import re, requests
from django.db import IntegrityError # for create_matches() when id is duplicate
from tournoi.models import Competition,Match,Club

# used by views.bookmarklet_receiver() and views.extract_matches()
def create_matches(match_ids: list[str], competition: str|Competition) -> list[str] | None:
    """Using the list `match_ids`, create the Match items (linked to `competition`) in our database.
    Return a list of warnings (duplicate match id's). If competition isn't found, return False."""
    if isinstance(competition, str):
        competition = Competition.objects.filter(name=competition).first()
        if not competition: return False
    warnings = []
    for m_id in match_ids:
        # get_or_create prevents duplicates if the button is clicked twice
        # BUT we can get an exception if the same match is linked to a different competition!
        try: Match.objects.get_or_create( id=m_id, competition=competition,
                defaults={'name': '', 'status': ''} ) # or: status=='unknown' ?
                # If the match_id already exists, but is linked to another competition:
        except IntegrityError: m_id = '0'+m_id ; Match.objects.get_or_create(
                id=m_id, competition=competition, defaults={'name': '', 'status': ''}
            );  warnings.append(f"Match '{m_id}' en double - informez un admin!")
    return warnings


def extract_match_ids_from_HTML(HTML, pattern = "/club/matches/"):
    # dd is for cutoff_date and debug info
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
                match_ids . append( (m_id.split("/")[idx := -1] if '/' in m_id # remove club name if it was 'inserted'
                                else m_id).split("?")[0]) # remove query string if present
                while not match_ids[-1].isdecimal(): # on some older pages there's a trailing "/games"
                    idx -= 1 # won't work anyways if there was no '/' ...
                    match_ids[-1]=m_id.split("/")[idx] # fingers crossed... -2 should better work at once
        elif 'off' in line:
            dd['num_off'] += 1
            for m in cutoff_regex.findall(line):
                cutoff_date[m] = cutoff_date.get(m, 0) + 1
        elif match_ids and stop_pattern in line: break
    return match_ids
