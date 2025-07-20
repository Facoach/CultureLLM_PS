
function showCustomPopup(message, duration = 3000, width = '300px', height = 'auto') {
    // Rimuovi eventuali popup esistenti per evitare sovrapposizioni
    const existingPopup = document.getElementById('customPopup');
    if (existingPopup) {
        existingPopup.remove();
    }

    // Crea l'elemento div per il popup
    const popup = document.createElement('div');
    popup.id = 'customPopup';
    popup.style.position = 'fixed';
    popup.style.top = '20px';
    popup.style.left = '50%';
    popup.style.transform = 'translateX(-50%)';
    popup.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    popup.style.color = 'white';
    popup.style.padding = '15px 25px';
    popup.style.borderRadius = '8px';
    popup.style.zIndex = '10000';
    popup.style.fontFamily = 'Arial, sans-serif';
    popup.style.fontSize = '16px';
    popup.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
    popup.style.display = 'flex';
    popup.style.alignItems = 'center';
    popup.style.justifyContent = 'space-between'; // Per allineare testo e bottone
    popup.style.opacity = '0';
    popup.style.transition = 'opacity 0.5s ease-in-out';

    // *** Nuove proprietà per dimensione fissa ***
    popup.style.width = width;
    popup.style.height = height;
    popup.style.boxSizing = 'border-box'; // Include padding e border nella larghezza/altezza
    popup.style.overflow = 'auto'; // Aggiunge scrollbar se il contenuto è troppo grande

    // Crea l'elemento span per il messaggio
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    messageSpan.style.flexGrow = '1'; // Permette al testo di occupare lo spazio disponibile
    popup.appendChild(messageSpan);

    // Crea il pulsante di chiusura
    const closeButton = document.createElement('button');
    closeButton.textContent = 'X';
    closeButton.style.background = 'none';
    closeButton.style.border = '1px solid white'; // Aggiunto un bordo per visibilità
    closeButton.style.color = 'white';
    // *** Regolazioni per bottone più piccolo ***
    closeButton.style.fontSize = '12px'; // Dimensione del font più piccola
    closeButton.style.width = '20px';    // Larghezza fissa
    closeButton.style.height = '20px';   // Altezza fissa
    closeButton.style.lineHeight = '1';  // Allinea verticalmente la 'X'
    closeButton.style.display = 'flex';
    closeButton.style.justifyContent = 'center';
    closeButton.style.alignItems = 'center';
    closeButton.style.cursor = 'pointer';
    closeButton.style.marginLeft = '15px'; // Spazio tra testo e bottone
    closeButton.style.borderRadius = '50%'; // Rende il bottone rotondo
    closeButton.style.transition = 'background-color 0.3s ease, border-color 0.3s ease';

    closeButton.onmouseover = () => {
        closeButton.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
        closeButton.style.borderColor = 'white'; // Mantieni il bordo bianco all'hover
    };
    closeButton.onmouseout = () => {
        closeButton.style.backgroundColor = 'none';
    };

    closeButton.onclick = () => {
        popup.style.opacity = '0';
        setTimeout(() => {
            popup.remove();
        }, 500);
        clearTimeout(timer);
    };
    popup.appendChild(closeButton);

    // Aggiungi il popup al body della pagina
    document.body.appendChild(popup);

    // Fai apparire il popup con una transizione
    setTimeout(() => {
        popup.style.opacity = '1';
    }, 10);

    // Imposta il timer per la chiusura automatica
    const timer = setTimeout(() => {
        popup.style.opacity = '0';
        setTimeout(() => {
            popup.remove();
        }, 500);
    }, duration);
}

// Mappa i nomi dei tab agli endpoint da cui caricare il loro contenuto
const tabEndpoints = {
    'ask': '/get_tab_content/ask',
    'leaderboard': '/get_tab_content/leaderboard',
    'answer': '/get_tab_content/answer'
};

// Gestisce il submit dei form con metodo POST nelle tab
function handlePostSubmitEvent(event) {
    handleFormSubmission(event, 'POST');
}

// Gestisce il submit dei form con metodo GET nelle tab
function handleGetSubmitEvent(event) {
    handleFormSubmission(event, 'GET');
}

// Inizializza i listener per tutti i form contenuti nei tab ed 
// aggancia il rispettivo gestore (visti sopra) in base al metodo (GET o POST)
function initializeTabForms() {
    document.querySelectorAll('.tab-content form').forEach(form => {
        const submitMethod = form.method.toUpperCase();

        if (submitMethod === 'POST') {
            form.removeEventListener('submit', handlePostSubmitEvent);
            form.addEventListener('submit', handlePostSubmitEvent);
        } else if (submitMethod === 'GET') {
            form.removeEventListener('submit', handleGetSubmitEvent);
            form.addEventListener('submit', handleGetSubmitEvent);
        }
    });


}


// Gestisce l'invio asincrono di un form (GET o POST), aggiorna dinamicamente il 
// contenuto della tab, mostra messaggio di caricamento, gestisce errori e redirect su login scaduto.
async function handleFormSubmission(event, method) {
    event.preventDefault();

    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
    }
    // Trova il contenitore del tab relativo al form
    const tabContentContainer = form.closest('.tab-content');
    if (tabContentContainer) {
        tabContentContainer.innerHTML = 'Esecuzione in corso...';
    }

    const url = form.action;
    let options = { method: method };
    // Se POST, invia i dati come FormData
    if (method === 'POST') {
        options.body = new FormData(form);
    }

    try {
        const response = await fetch(url, options);
        // Se la risposta non è ok, tenta di mostrare il dettaglio dell'errore
        if (!response.ok) {
            let detail = "Errore durante l'operazione.";
            try {
                const errorJson = await response.json();
                if (errorJson && errorJson.detail) {
                    detail = errorJson.detail;
                }
            } catch (e) {
                // Se la risposta non è JSON la ignora
            }
            throw new Error(`HTTP error! status: ${response.status} - ${detail}`);
        }

        const updatedHtml = await response.text();

        // Controlla se la redirect è un login (la sessione è scaduta), in quel caso non va 
        // impostato come innerthml e reindirizza
        if (updatedHtml.includes('id="login-form-container"') || response.url.includes('/directlogin')) {
            console.log("Rilevata pagina di login. Reindirizzamento...");
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }
        // Aggiorna il tab con il nuovo contenuto HTML e reinizializza i form
        if (tabContentContainer) {
            tabContentContainer.innerHTML = updatedHtml;
            initializeTabForms();

            if (form.action.includes('/answer') && updatedHtml.toLowerCase().includes('risposta aggiunta con successo')) {
                showCustomPopup("+40 punti saranno assegnati se la tua risposta sarà scelta come migliore");
            }

            if (form.action.includes('/ask') && updatedHtml.toLowerCase().includes('domanda aggiunta con successo')) {
                showCustomPopup("+10 punti per aver posto una domanda");
            }
        }

    } catch (error) {
        console.error("Errore nell'invio del form o nel caricamento del contenuto:", error);
        if (tabContentContainer) {
            tabContentContainer.innerHTML = `<p style="color: red;">Errore durante l'aggiornamento: ${error.message}</p>`;
        }
    } finally {
        if (submitButton) {
            submitButton.disabled = false; // Riabilita il pulsante
        }
    }
}


// Attiva la visualizzazione di un tab specifico ed aggiorna le classi
// CSS per mostrare/nascondere il contenuto delle tab e i pulsanti.
async function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));

    document.getElementById(`${tabName}-content`).classList.add('active');
    document.querySelector(`.tab-button[data-tab-name="${tabName}"]`).classList.add('active');
}


// Carica tramite fetch il contenuto HTML di tutti i tab dal backend e aggiorna 
// le rispettive sezioni, gestisce anche eventuali reindirizzamenti al login.
async function loadAllTabContents() {
    for (const tabName in tabEndpoints) {
        const endpointUrl = tabEndpoints[tabName];
        const contentContainer = document.getElementById(`${tabName}-content`);
        contentContainer.innerHTML = `Caricamento ${tabName}...`;

        try {
            const response = await fetch(endpointUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const htmlContent = await response.text();

             // Controlla se la redirect è un login (la sessione è scaduta), in quel caso non va 
            // impostato come innerthml e reindirizza
            if (htmlContent.includes('id="login-form-container"') || response.url.includes('/directlogin')) {
                console.log("Rilevata pagina di login durante il caricamento del tab. Reindirizzamento...");
                window.location.href = '/directlogin?message=Token scaduto o assente';
                return;
            }

            contentContainer.innerHTML = htmlContent;
        } catch (error) {
            console.error(`Errore nel caricamento del tab ${tabName}:`, error);
            contentContainer.innerHTML = `<p style="color: red;">Errore nel caricamento del tab ${tabName}.</p>`;
        }
    }
    initializeTabForms();
    // Di default mostra il tab "ask"
    showTab('ask');
}


// Inizializza i tab e listener una volta che il DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    // Carica tutti i contenuti dei tab
    loadAllTabContents();
    // Listener per i pulsanti dei tab (Ask, Answer, Leaderboard)
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tabName;
            showTab(tabName);
        });
    });
    
});


// Invia la richiesta di validazione della domanda all'endoint /validate e
// gestisce la logica di visualizzazione della domanda e delle risposte
// per poter scegliere la migliore
function loadValidate(questionId) {
    fetch('/validate', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        body: `questionid=${questionId}`
    })
    .then(r => {
        // Se la risposta è una redirect al login, reindirizza
        if (r.url.includes('/directlogin')) {
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }
        return r.json();
    })
    .then(d => {
        const answers = d.answers || [];
        // Lista che contiene gli id nell'ordine in cui si trovano in 
        //answers dopo lo shuffle, con successivo encoding
        let id_order = answers.map(x => x[0]);
        const id_order_json = encodeURIComponent(JSON.stringify(id_order));
        // Se è stata già valutata mostra solo la domanda e la risposta scelta come migliore
        if(d.checked == 1) {
            document.getElementById('chat-view').innerHTML = `
                <div class="question-main">
                    <div class="main-question">${d.question[1]}</div>
                </div>
                <div class="best-answer-block">
                    <div class="best-title">Risposta migliore</div>
                    <div class="best-answer">${answers.length > 0 ? d.best_answer : "<em>Non disponibile</em>"}</div>
                </div>
            `;
        // Se non ci sono ancora tutte e 4 le risposte mostra un messaggio di attesa
        } else if(answers.length < 4) {
            document.getElementById('chat-view').innerHTML = `
                <div class="question-main">
                    <div class="main-question">${d.question[1]}</div>
                </div>
                <div class="waiting-message">
                    <span>In attesa delle risposte...</span>
                </div>
            `;
        } 
        // Mostra le 4 risposte come bottoni per scegliere la migliore
        else {
            const answerBlocks = [];
            for(let i=0; i<4; i++) {
                const answer = answers[i];
                answerBlocks.push(`
                    <button class="answer-cell" onclick="sendBest(${d.question[0]},${answer[0]},'${id_order_json}'); showCustomPopup('+40 a chi ha dato la risposta')">
                        <div class="answer-title">Risposta ${i + 1}</div>
                        <div class="answer-text">${answer[1]}</div>
                    </button>
                `);
            }
            document.getElementById('chat-view').innerHTML = `
                <div class="question-main">
                    <div class="main-question">${d.question[1]}</div>
                    <div class="sub-message">Scegli la risposta migliore tra quelle proposte:</div>
                </div>
                <div class="answers-grid">
                    ${answerBlocks.join('')}
                </div>
            `;
        }
    })
    .catch(err => console.error(err));
}


//  Gestisce la scelta da parte dell'utente di quale sia la rispostsa umana
// tra le opzioni, mantiene lo shuffle delle risposte tramite id_order_json
function sendBest(questionId, answerId, id_order_json) {
    fetch('/best', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        body: `questionid=${questionId}&answerid=${answerId}`
    })
    .then(r => {
        // Se la risposta è una redirect al login, reindirizza
        if (r.url.includes('/directlogin')) {
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }
        return r.json();
    })
    .then(d => {
        const answers = d.answers || [];
        // Parsa la lista degli id in ordine (shuffled) ad un array
        let id_order = [];
        if (typeof id_order_json === "string") {
            id_order = JSON.parse(decodeURIComponent(id_order_json));
        }
        // Sorta answers seguendo l'ordine degli id nella lista in_order (per mantenere lo shuffle)
        answers.sort((a, b) => id_order.indexOf(a[0]) - id_order.indexOf(b[0]));
        // Prepara i blocchi risposta (alcuni potrebbero essere in attesa)
        const answerBlocks = [];
        for(let i=0; i<4; i++) {
            const answer = answers[i];
            if (!answer) {
                answerBlocks.push(`
                    <div class="answer-cell disabled">
                        <div class="answer-title">Risposta ${i+1}</div>
                        <div class="answer-text pending"><em>In attesa...</em></div>
                    </div>
                `);
            }
            else {
                if (answer[2]!=-1){
                    answerBlocks.push(`
                        <form action="/get_tab_content/ask" method="GET">
                            <button type= "submit" class="answer-cell" onclick="sendHuman(${answer[2]}, ${d.question[0]}); showCustomPopup('+10 punti, era la risposta di un utente!')">
                                <div class="answer-title">Risposta ${i+1}</div>
                                <div class="answer-text">${answer[1]}</div>
                            </button>
                        </form>
                    `);
                }
                else {
                    answerBlocks.push(`
                        <form action="/get_tab_content/ask" method="GET">
                            <button type= "submit" class="answer-cell" onclick="sendHuman(${answer[2]}, ${d.question[0]}); showCustomPopup('Purtroppo era una risposta data da IA')">
                                <div class="answer-title">Risposta ${i+1}</div>
                                <div class="answer-text">${answer[1]}</div>
                            </button>
                        </form>
                    `);
                }
            }
        }
        document.getElementById('chat-view').innerHTML = `
            <div class="question-main">
                <div class="main-question">${d.question[1]}</div>
                <div class="sub-message">Ora indica quale risposta pensi sia scritta da un umano:</div>
            </div>
            <div class="answers-grid">
                ${answerBlocks.join('')}
            </div>
        `;
        initializeTabForms();
    })
    .catch(err => console.error(err));
}


// Dopo la scelta della risposta "umana", mostra solo il messaggio di conferma
function sendHuman(humanId, questionId) {
    fetch('/human', {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded'},
        body: `human=${humanId}&questionid=${questionId}`
    })
    .then(r => {
        // Se la risposta è una redirect al login, reindirizza
        if (r.url.includes('/directlogin')) {
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }
        return r.json();
    })
    .then(d => {
        document.getElementById('chat-view').innerHTML = `
            <div class="waiting-message">
                ${d.message}
            </div>
        `;
    })
    .catch(err => console.error(err));
}


// Controlla ogni 5 secondi se ci sono nuove risposte per le domande in lavorazione,
// in tal caso mostra il pallino di notifica accanto alle domande corrispondenti.
function checkNewAnswers() {
    fetch('/check_new_answers')
    .then(res => {
        if (res.url.includes('/directlogin')) {
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }
        return res.json();
    })
    .then(data => {
        // Scorre tutti i bottoni delle domande in lavorazione
        document.querySelectorAll('.question-card.in-progress .question-title').forEach(button => {
            const qId = button.getAttribute('data-questionid');
            const notifDot = button.querySelector('.notif-dot');
            // Se l'id della domanda è tra quelle con nuove risposte, mostra il pallino
            if (data.new_answers.includes(parseInt(qId))) {
                notifDot.style.display = 'inline-block';
            } else {
                notifDot.style.display = 'none';
            }
        });
    })
    .catch(err => console.error(err));
}
setInterval(checkNewAnswers, 5000);


// Aggiorna la leaderboard ogni 5 secondi
async function refreshLeaderboard() {
    const leaderboardContainer = document.getElementById('leaderboard-content');
    if (!leaderboardContainer) {
        console.error("Contenitore della leaderboard non trovato.");
        return;
    }

    try {
        const response = await fetch('/get_tab_content/leaderboard');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const htmlContent = await response.text();

        // Controlla se la redirect è un login (la sessione è scaduta), in quel caso non va impostato come innerthml
        if (htmlContent.includes('id="login-form-container"') || response.url.includes('/directlogin')) {
            console.log("Rilevata pagina di login durante l'aggiornamento della leaderboard. Reindirizzamento...");
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }

        leaderboardContainer.innerHTML = htmlContent;
        // Una volta aggiornato il contenuto, se ci fossero form al suo interno,
        // è buona pratica reinizializzare i loro listener.
        initializeTabForms();
    } catch (error) {
        console.error("Errore durante l'aggiornamento della leaderboard:", error);
    }
}
setInterval(refreshLeaderboard, 5000);


// Aggiunge un event listener sull'evento 'pagehide', che viene chiamato 
// quando l'utente chiude la pagina
window.addEventListener('pagehide', function(event){
    if(!event.persisted){
        const logoutEndpoint = '/logout';
    const data = JSON.stringify({ message: 'User logging out' });

    // Controlla se sendBeacon è supportato dal browser, in tal caso lo usa per mandare la
    // richiesta di logout in modo affidabile, altrimenti usa fetch anche se meno affidabile
    if (navigator.sendBeacon) {
        navigator.sendBeacon(logoutEndpoint, data);
        console.log('Logout beacon sent.');
    } else {
        console.warn('navigator.sendBeacon not supported. Attempting less reliable logout.');
        fetch(logoutEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: data,
        keepalive: true
        }).catch(error => {
        console.error('Error sending logout request (fallback):', error);
        });
    }
    }
});