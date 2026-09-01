javascript:(function(){/*** DON'T USE // : this is pasted into bookmark-URL field! ***/

/* 1. FIND THE CONTAINER USING THE FIRST MATCH LINK */
    let firstLink = document.querySelector('a[href*="chess.com/club/matches/"]');
    let opContainer = document;
    if (firstLink) {
        let currentDiv = firstLink.closest('div');
        while (currentDiv && currentDiv.innerText.length < 100 && currentDiv.parentElement) {
            currentDiv = currentDiv.parentElement.closest('div');
        }
        if (currentDiv) { opContainer = currentDiv; }
    }

    /* 2. GRAB ONLY MATCH LINKS INSIDE THAT CONTAINER */
    let matchIds = Array.from(opContainer.querySelectorAll('a[href*="chess.com/club/matches/"]'))
        .map(a => (a.href.match(/\/(\d+)(?!\w)/) || [])[1])
        .filter(Boolean);
        
    let uniqueMatchIds = [...new Set(matchIds)];

/* 3. DATES & other PAYLOAD */
    let postText = opContainer.innerText;
    let startMatch = postText.match(/d[ée]marrage.*?(\d{2}\/\d{2}\/\d{4})/i);
    let cutoffMatch = postText.match(/cut+[- ]off.*?(\d{2}\/\d{2}\/\d{4})/i);
    
/* 3. Send this to our web app */
fetch('https://cfe.pythonanywhere.com/api/receive-links/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        token: 'my-super-secret-token-88372', /* Must match your Django view */
        url: window.location.href,            /* The URL you are currently on*/
        match_ids: uniqueMatchIds,
        start_date: startMatch ? startMatch[1] : null,
        cutoff_date: cutoffMatch ? cutoffMatch[1] : null
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) { alert(data.message); } 
    else { alert("Error: " + data.error); }
})
.catch(err => alert("Failed to connect: " + err));

})();
/*end JS booklet*/
