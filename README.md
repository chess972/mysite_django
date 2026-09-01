# Gestion CFE-LFR-CFT

This django web app is for managing medium sized inter-club ("daily") competitions on chess.com (= C.C below).
Specifically, it is currently designed for the CFE / LFR / CFT competitions,
validated by chess.com_fr.

These competitions are announced on C.C forums. A club announcement or forum page will
"define" each "competition", which might be, e.g. "CFE 2026 D1" or "CFT 2027 Phases finales"
or "LFR 2026 U1400 Top Final".

Each of these competitions consists of several matches ("rencontres") where one club plays against another club.

These matches are specified on the "announcement" page through a link as, e.g., https://www.chess.com/club/matches/1993118.

The web app collects all the links to matches on a given competion announcement page
and then allows to track the progress of the matches and finally establish ome or more ranking tables,
called "tableau(x) de classement".

The web app also allows to display the list of participating clubs, several stats and in particular a list of players 
that play for different teams in one given competition (which is forbidden).

...

(more to be added later).


