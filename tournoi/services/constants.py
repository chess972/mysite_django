""" mysite_django/tournoi/services/constants.py

Constants for the "services" package.

"""

# Le dict suivant donne le nouveau nom pour l'ancien nom, quand un club a été renommé
# ou entièrement remplacé par un autre [et désactivé].
# En gros, seulement si https://www.chess.com/club/ANCIEN ne fonctionne plus
# (même si parfois, https://api.chess.com/pub/club/ANCIEN fonctionne encore.)

aliases = {
    # voir aussi: https://docs.google.com/document/d/1ZrB3Wt947U2VhRUhonE2_Wv0irX-McWScKqV5XVVAK4/
    # keys = clubs qui N'EXISTENT PLUS (URL https://www.chess.com/club/xxx => 404)
    'normandie': # "Ce club a été désactivé." (en avril 2025 ?)
        'echiquier-de-normandie', # créé 15.4.2025
    'paris-neuf-trois':     # n'existe plus:
        'saint-denis-93-chess',	    # créé 1.6.2024, renommé en juin 2026
    'team-grand-est-1': # n'existe plus. a participé en CFE 2022 ; en ..., Grand Est = ''
        'region-grand-est', # créé ... .
        # A NOTER:
        # 'the-ruy-lopez-opening...' # a participé en tant que "Grand Est" en ...
        # Ce club existe toujours !
        # TODO : put references here.
    'region-mayotte': # n'existe plus (ni www, ni api)
        'team-mayotte-mahorais-chess-club', # créé Apr 6, 2024
    #'isula-corsica':   # créé 16.5.2021, "Destiné à participer...dans les futures éditions...CFE"
    #   'corsica-chess-team-squadra-corsa-di-scacchi',  # créé 10.7.2026 . Les deux sont actifs

    #"team-orleans":    # créé 23.11.2022 ; existe toujours
    #   "team-orleans-le-cavalier-de-jeanne",   # créé 14.7.2026 (mais l'ancien existe toujours)

    #"les-cavaliers-de-brume":  # créé 23 Nov 2022. EXISTE TOUJOURS !
        # A NOTER: c'est une Association et un Club d'échecs reconnu, voir :
        #   voir :  https://www.echecs.asso.fr/FicheClub.aspx?Ref=3251
        #   et :    https://annuaire-entreprises.data.gouv.fr/entreprise/les-cavaliers-de-brume-934803701
        # "spm-975-chess-club",   # créé 7 Aug 2026, remplace le premier (qui reste actif) dans CFE/CFT/LFR

    #"la-reine-d-anjou":    # créé Mar 10, 2021, existe toujours (9/26)
    #   "team-pays-de-la-loire", #  créé Jul 16, 2021 ; renommé ? en juillet(?) 2026
}
