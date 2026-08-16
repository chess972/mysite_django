# tournoi/models.py - (c) 23-07-2026 by MFH
from django.db import models
from datetime import datetime

class Competition(models.Model):
    # for competitions, the ID we use is the "(short) name"
    # TODO: introduce slug: django.utils.text.slugify("CFE 2026 D1") -> 'cfe-2026-d1'
    # short name, e.g., "CFE 2026 D1"
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

    # The web page (e.g., https://www.chess.com/fr/clubs/forum/view/cfe2025-u1400)
    # where the competition is "defined", i.e., where the match_id's can be found.
    url = models.URLField(max_length=500)

    # Competition-wide cut-off date. (Use DateTimeField if you need exact times)
    # if current_data >= cutoff_date, the competition must be considered finished,
    # even if all games are not yet played.
    # The scores of the matches must no more be updated after this date
    cutoff_date = models.DateTimeField(null=True, blank=True)

    # when the competition (i.e., it's first match) is expected to start
    # (this < current_date <=> still in registration phase ;
    #  this > current_date <=> ongoing or finished.)
    start_date = models.DateTimeField(null=True, blank=True)

    # set true if it shouldn't be listed on the main list
    hidden = models.BooleanField(default=False)  # For archiving instead of deleting
    raw_data = models.JSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)
    year = models.IntegerField(default=0)
    class Meta:
        ordering = ['-year', '-sort_order', 'name']


# 1. The Abstract Base Class for Club & Match (not Competition)
class BaseModel(models.Model):
    """
    Abstract base class that provides a 'name' field and a standard __str__ method
    to all models that inherit from it. No database table is created for this class.
    """
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    class Meta:
        abstract = True

    def __str__(self): return self.name if self.name else n if (n:=self.raw_data
        )and (n:=n.get('name')) else self.id

    @property # so we can use `club.api` in Python
    def api(self): return self.api_prefix + self.id
    @property # so we can use `club.web_url` in Python or `{{ club.web_url }}` in HTML!
    def url(self): return self.url_prefix + self.id

    # we dump the whole API data dict here so we don't have to ping the API constantly
    raw_data = models.JSONField(null=True, blank=True)


# Club must be defined before Match which refers to this
class Club(BaseModel):
    api_prefix = "https://api.chess.com/pub/club/"
    url_prefix = "https://www.chess.com/club/"

    # id: e.g., 'grenoble-echecs-metropole', not 676203
    # (Now inherited from BaseModel.)
    #id = models.CharField(max_length=100, unique=True)

    # Now inherited from BaseModel:
    #name = models.CharField(max_length=100)
    # This is a possibly shorter name (e.g., "Isbergues" or "Tahiti")
    # which we use e.g. in the "classement" table instead of the full official name
    # (e.g. "La tour infernale", or "Fédération Tahitienne d'Echecs")

    # 3-letter abbreviation for the "tableau de classement"
    abbreviation = models.CharField(max_length=3, blank=True, null=True)


class Match(BaseModel):
    api_prefix = "https://api.chess.com/pub/match/"
    url_prefix = "https://www.chess.com/club/matches/"

    # This links the Match to the Competition.
    # related_name='matches' means you can do `my_compet.matches.all()`
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='matches')

    # inherited from BaseModel:
    #id = models.CharField(max_length=50, unique=True)  # e.g., '1952205'
    #name = models.CharField(max_length=200) # inherited
    #url = models.URLField() # computed through @property of baseModel

    # E.g., 'finished', 'registration', 'in_progress'
    # We might set this to "finished" when the cut-off date is (just) passed,
    # and then we set the "scores" below to their "final" value (as of cutoff date)
    # which MUST NOT be updated later,
    # even if the raw_api_data might get updated until all games are finished.
    status = models.CharField(max_length=50)

    # Connect matches to our clubs
    # Then we can use `home_matches = my_club.matches_as_team1.all()`
    # to get all matches where this club played as team1.
    team1 = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, related_name='matches_as_team1')#club1
    team2 = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, related_name='matches_as_team2')#club2

    # Store scores and boards directly for fast "tableau de classement" math
    score_team1 = models.FloatField(default=0)
    score_team2 = models.FloatField(default=0)
    num_boards = models.IntegerField(default=0)
    @property
    def end_date(self) -> datetime | None:
        try: return datetime.fromtimestamp(int(self.raw_data['end_time']))
        except (KeyError, ValueError, TypeError): return None

    @property
    def remaining(self):
        """Calculates games left: 2*boards - (score1 + score2), unless status='finished',
        which can also occur due to cut-off or cancellation [boards < min_boards].
        """
        return 0 if self.status=='finished' else 2*self.num_boards - round(
                                self.score_team1 + self.score_team2)
