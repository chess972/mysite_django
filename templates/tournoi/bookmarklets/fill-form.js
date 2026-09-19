javascript:(function(){/*** COPIER-COLLER TOUT ça dans le champ URL d'un signet ***/
    const API_URL = 'https://cfe.pythonanywhere.com/api/next-match/';
    const $ = s => document.querySelector(s);
    function set(select, value, spec=0) { /* spec : 0=normal, 1=date (readonly), 2=club (dropdown)*/
        const el = $(select);
        if (value === undefined || value === null | !el) return;
        /* Pré-traitement selon le cas spécial */
        switch (spec) { case 2: el.focus(); break;
            case 1: el.removeAttribute('readonly');
        }
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        /* Post-traitement selon le cas spécial */
        switch(spec){ case 1: el.setAttribute('readonly', 'readonly'); break;
        case 2: setTimeout(() => {
                const opt = $('.form-autocomplete-dropdown li');
                if (opt) opt.click() }, 500);
        }
    }
    fetch(API_URL)
        .then(res => {
            if (!res.ok) throw new Error('Erreur API ou aucun match');
            return res.json();
        })
        .then(data => {
            if (!data || data.length === 0) throw new Error('Aucun match');
            /* Création du texte pour la boîte de choix */
            let texte = 'Choisissez un match à créer :\n';
            data.forEach((m, i) => { texte += (i + 1) + ' - ' + m.titre + '\n'; });
            /* Affichage de la boîte de dialogue (par défaut le choix 1) */
            let choix = prompt(texte, '1');
            if (choix === null) return; /* L'utilisateur a cliqué sur Annuler */
            let index = parseInt(choix) - 1;
            if (isNaN(index) || index < 0 || index >= data.length) throw new Error('Choix invalide');
            const match = data[index];
            set('input[placeholder="Titre"]', match.titre);
            set('textarea', match.description);
            set('input[name="min-players"]', match.min_players);
            set('input[name="max-players"]', match.max_players);
            set('input[name="min-rating"]', match.min_rating);
            set('input[name="max-rating"]', match.max_rating);
            set('select[name="min-required-games"]', match.min_games);
            /* Les cas spéciaux utilisent le 3ème paramètre */
            set('.datepicker-input-component input', match.date, 1);
            set('input[placeholder="Trouver un club..."]', match.club_invite_name, 2);
            /*alert('Match pré-rempli : ' + match.titre);*/
        })
        .catch(err => alert('Erreur : ' + err.message));
})();
