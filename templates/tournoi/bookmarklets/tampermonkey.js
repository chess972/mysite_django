// ==UserScript==
// @name         Assistant Remplissage Formulaire Création rencontre CFE-LFR-CFT
// @namespace    http://tampermonkey.net/
// @version      2026-08-18
// @description  Automatisattion remplissage formulaire création de match de club en différé
// @author       M.F.H.
// @match        https://gemini.google.com/app/6cc632b08b184fcf
// @icon         https://www.google.com/s2/favicons?sz=64&domain=google.com
// @match        https://www.chess.com/play/online/create-tournament*
// @other        https://www.chess.com/play/online*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    // 1. Collez ici le résultat JSON généré par votre script Python
    let MES_MATCHS = [
      {
        "titre": "LFR J1 : Grenoble vs Antilles",
        "description": "Match officiel LFR entre Grenoble Echecs Metropole et Team French Antilles.\nBonne chance aux deux équipes !",
        "club_hote_id": "689141", // Remplacez par le vrai ID du club hôte
        "club_invite_name": "Team French Antilles",
        "days_per_move": "3",
        "min_players": "5",
        "max_players": "15",
        "min_rating": "1000",
        "max_rating": "2200",
        "games_per_player": "2",
          "date": "05/10/2026", // <--- Format JJ/MM/AAAA
        "min_games": "5",
      }
    ];
    // Helper pour mettre à jour la valeur d'un champ texte/textarea et notifier Vue.js
    function setInputValue(element, value) {
        if (!element) return;
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
    }
    // Helper pour cibler un champ à partir du texte de son libellé
    function getFieldByLabel(labelSubstring) {
        const labels = Array.from(document.querySelectorAll('.club-event-field-label'));
        const target = labels.find(l => l.textContent.toLowerCase().includes(labelSubstring.toLowerCase()));
        return target ? target.closest('.club-event-field-component') : null;
    }
    // Helper pour injecter une valeur de l'objet 'match' dans le DOM
    function injecterChamp(match, cle, selecteur = null) {
        const valeur = match[cle]; if (valeur === undefined || valeur === null) return;
        // Convertir "min_players" -> "min-players" pour cibler l'attribut name
        const nameAttr = cle.replace(/_/g, '-');
        // Si aucun sélecteur n'est fourni, on cherche par name="cle" ou name="cle-modifiée"
        const targetSelector = selecteur || `input[name="${nameAttr}"], select[name="${nameAttr}"]`;
        const element = document.querySelector(targetSelector);
        if (element) setInputValue(element, valeur);
    }

    function remplirFormulaire(match) {
        // 1. Utilisation du helper pour les champs simples
/*      // C. Titre du match & Description
        //setInputValue(document.querySelector('input[placeholder="Titre"]'), match.titre);
        //setInputValue(document.querySelector('textarea'), match.description);
        // E. Nombre de joueurs (Min / Max)
        //setInputValue(document.querySelector('input[name="min-players"]'), match.min_players);
        //setInputValue(document.querySelector('input[name="max-players"]'), match.max_players);
        // G. Classement (Min / Max)
        //setInputValue(document.querySelector('input[name="min-rating"]'), match.min_rating);
        //setInputValue(document.querySelector('input[name="max-rating"]'), match.max_rating);
        // I. Minimum de parties requises
        //setInputValue(document.querySelector('select[name="min-required-games"]'), match.min_games);
*/
        injecterChamp(match, 'titre', 'input[placeholder="Titre"]');
        injecterChamp(match, 'description', 'textarea');
        injecterChamp(match, 'min_players');//, 'input[name="min-players"]'
        injecterChamp(match, 'max_players');//, 'input[name="max-players"]'
        injecterChamp(match, 'min_rating');//, 'input[name="min-rating"]'
        injecterChamp(match, 'max_rating');//, 'input[name="max-rating"]'
        injecterChamp(match, 'min_games', 'select[name="min-required-games"]');

        // 2. Remplissage des champs basés sur le texte de leur Label
/*      // A. Sélection du Club Hôte
        const clubHostField = getFieldByLabel("Club");
        if (clubHostField) {
            const select = clubHostField.querySelector('select');
            if (select) setInputValue(select, match.club_hote_id);
        }
        // B. Type à défier ("Club")
        const challengeField = getFieldByLabel("Club à défier");
        if (challengeField) {
            const select = challengeField.querySelector('select');
            if (select) setInputValue(select, "club");
        }
        // F. Jours par coup
        const daysField = getFieldByLabel("Jours par coup");
        if (daysField) setInputValue(daysField.querySelector('select'), match.days_per_move);
        // H. Parties simultanées par joueur
        const simGamesField = getFieldByLabel("Parties simultanées");
        if (simGamesField) setInputValue(simGamesField.querySelector('select'), match.games_per_player);
*/
    const injecterParLabel = (labelTexte, valeur) => {
        const field = getFieldByLabel(labelTexte);
        if (field) {
            const el = field.querySelector('select, input');
            if (el) setInputValue(el, valeur);
        }
    };
    injecterParLabel("Club", match.club_hote_id);
    injecterParLabel("Club à défier", "club");
    injecterParLabel("Jours par coup", match.days_per_move);
    injecterParLabel("Parties simultanées", match.games_per_player);

        // D. Date (contournement de l'attribut readonly)
        const dateInput = document.querySelector('.datepicker-input-component input');
        if (dateInput && match.date) {
            dateInput.removeAttribute('readonly');
            setInputValue(dateInput, match.date);
            dateInput.setAttribute('readonly', 'readonly');
        }

        // B.2 Recherche ET Sélection du club adverse
    // Remplissage de la recherche du club adverse
    // Déclenche l'affichage du menu des suggestions après un très court délai
    setTimeout(() => {
        const clubSearchInput = document.querySelector('input[placeholder="Trouver un club..."]');
        if (clubSearchInput && match.club_invite_name) {
            clubSearchInput.focus();
            setInputValue(clubSearchInput, match.club_invite_name);
            // On attend 500ms que la liste des résultats de recherche s'affiche, puis on clique
            setTimeout(() => {
                const firstOption = document.querySelector('.form-autocomplete-dropdown li');
                if (firstOption) {
                    firstOption.click();
                }
            }, 500);
        }// end if
    }, 300);

        alert(`Formulaire pré-rempli pour : ${match.titre}\nN'oubliez pas de confirmer le choix du club adverse dans le champ de recherche dédié.`);
    }

    // Création de l'interface d'administration
    function InsererPanneau() {
        if (document.getElementById('lfr-admin-panel')) return;

        const panel = document.createElement('div');
        panel.id = 'lfr-admin-panel';
        panel.style.cssText = `
            position: fixed; top: 80px; right: 20px; z-index: 999999;
            background: #262421; color: white; padding: 15px;
            border-radius: 8px;  border: 2px solid #81b64c; width: 260px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5); font-family: sans-serif;
        `;
        panel.innerHTML = `
            <h4 style="margin: 0 0 10px 0; color: #81b64c;">Assistant LFR / CFE</h4>
       <button id="lfr-btn-load" style="width:100%; padding:6px; background:#454341; color:white; border:none; border-radius:4px; cursor:pointer; margin-bottom:10px;">
                🔄 Charger depuis la WebApp
       </button>
          <label style="font-size: 12px;">Choisir une rencontre :</label>
            <select id="lfr-match-select" style="width: 100%; margin-top: 5px; padding: 6px; background: #312e2b; color: white; border: 1px solid #454341; border-radius: 4px;"></select>
            <button id="lfr-btn-inject" style="width: 100%; margin-top: 12px; padding: 8px; background: #81b64c; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">
                 Injecter dans le formulaire
            </button>
        `;
        document.body.appendChild(panel);

        const updateDropdown = () => {
            const select = document.getElementById('lfr-match-select');
            select.innerHTML = '';
            MES_MATCHS.forEach((m, idx) => {
                const opt = document.createElement('option');
                opt.value = idx;
                opt.textContent = m.titre;
                select.appendChild(opt);
            });
        };
        // Bouton pour charger le JSON généré par Python
        document.getElementById('lfr-btn-load').onclick = () => {
/*
            fetch('http://localhost:8000/matchs_lfr.json')
                .then(res => res.json())
                .then(data => {
                    MES_MATCHS = data;
                    updateDropdown();
                    alert(`${data.length} match(s) chargé(s) avec succès !`);
                })
                .catch(err => alert("Erreur : Assurez-vous que le script Python est lancé et écoute sur le port 8000."));
*/
            GM_xmlhttpRequest({
        method: "GET",
        url: "https://cfe.pythonanywhere.com/create_match_data/",
        onload: function(response) {
            MES_MATCHS = JSON.parse(response.responseText);
            updateDropdown();
            alert(`${MES_MATCHS.length} match(s) chargé(s) depuis la ligue !`);
        },
        onerror: function(err) {
            alert("Erreur de connexion avec cfe.pythonanywhere.com");
        }
            });
        };

        document.getElementById('lfr-btn-inject').onclick = () => {
            const index = document.getElementById('lfr-match-select').value;
            if (MES_MATCHS[index]) remplirFormulaire(MES_MATCHS[index]);
        };
    }
    // Observer pour détecter quand la modal de formulaire apparaît à l'écran
    const observer = new MutationObserver(() => {
        if (document.querySelector('.club-event-form-component')) InsererPanneau();
    });
    observer.observe(document.body, { childList: true, subtree: true });
})();
