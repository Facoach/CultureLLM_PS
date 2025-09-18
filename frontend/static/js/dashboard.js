
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

    // *** proprietà per dimensione fissa ***
    popup.style.width = width;
    popup.style.height = height;
    popup.style.boxSizing = 'border-box'; 
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
    closeButton.style.border = '1px solid white';
    closeButton.style.color = 'white';
    closeButton.style.fontSize = '12px'; // Dimensione del font
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
        closeButton.style.borderColor = 'white';
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
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `questionid=${questionId}`
    })
    .then(r => {
        if (r.url.includes('/directlogin')) {
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }
        return r.json();
    })
    .then(d => {
        const chatView = document.getElementById('chat-view');
        chatView.innerHTML = ''; // Pulisce il contenuto precedente

        const answers = d.answers || [];
        const id_order = answers.map(x => x[0]);
        const id_order_json = encodeURIComponent(JSON.stringify(id_order));

        // Contenitore principale della domanda
        const questionMain = document.createElement('div');
        questionMain.className = 'question-main';

        const mainQuestion = document.createElement('div');
        mainQuestion.className = 'main-question';
        mainQuestion.textContent = d.question[1]; // ✅ Sicuro

        questionMain.appendChild(mainQuestion);
        chatView.appendChild(questionMain);

        if (d.checked == 1) {
            // Se è già stata valutata, mostra solo la risposta migliore
            const bestBlock = document.createElement('div');
            bestBlock.className = 'best-answer-block';

            const bestTitle = document.createElement('div');
            bestTitle.className = 'best-title';
            bestTitle.textContent = 'Risposta migliore';

            const bestAnswer = document.createElement('div');
            bestAnswer.className = 'best-answer';

            if (answers.length > 0) {
                bestAnswer.textContent = d.best_answer; // ✅ Sicuro
            } else {
                const em = document.createElement('em');
                em.textContent = 'Non disponibile';
                bestAnswer.appendChild(em);
            }

            bestBlock.appendChild(bestTitle);
            bestBlock.appendChild(bestAnswer);
            chatView.appendChild(bestBlock);
        }

        else if (answers.length < 4) {
            // Messaggio di attesa
            const waitingMessage = document.createElement('div');
            waitingMessage.className = 'waiting-message';

            const span = document.createElement('span');
            span.textContent = 'In attesa delle risposte...';
            waitingMessage.appendChild(span);

            chatView.appendChild(waitingMessage);
        }

        else {
            // Mostra le risposte per la selezione
            const subMessage = document.createElement('div');
            subMessage.className = 'sub-message';
            subMessage.textContent = 'Scegli la risposta migliore tra quelle proposte:';
            questionMain.appendChild(subMessage);

            const answersGrid = document.createElement('div');
            answersGrid.className = 'answers-grid';

            for (let i = 0; i < 4; i++) {
                const answer = answers[i];

                const button = document.createElement('button');
                button.className = 'answer-cell';
                button.onclick = () => {
                    sendBest(d.question[0], answer[0], id_order_json);
                    showCustomPopup('+40 a chi ha dato la risposta');
                };

                const title = document.createElement('div');
                title.className = 'answer-title';
                title.textContent = `Risposta ${i + 1}`;

                const text = document.createElement('div');
                text.className = 'answer-text';
                text.textContent = answer[1]; // ✅ Sicuro

                button.appendChild(title);
                button.appendChild(text);
                answersGrid.appendChild(button);
            }

            chatView.appendChild(answersGrid);
        }

    })
    .catch(err => console.error(err));
}



//  Gestisce la scelta da parte dell'utente di quale sia la rispostsa umana
// tra le opzioni, mantiene lo shuffle delle risposte tramite id_order_json
function sendBest(questionId, answerId, id_order_json) {
    fetch('/best', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `questionid=${questionId}&answerid=${answerId}`
    })
    .then(r => {
        if (r.url.includes('/directlogin')) {
            window.location.href = '/directlogin?message=Token scaduto o assente';
            return;
        }
        return r.json();
    })
    .then(d => {
        const answers = d.answers || [];

        let id_order = [];
        if (typeof id_order_json === "string") {
            id_order = JSON.parse(decodeURIComponent(id_order_json));
        }

        answers.sort((a, b) => id_order.indexOf(a[0]) - id_order.indexOf(b[0]));

        const chatView = document.getElementById('chat-view');
        chatView.innerHTML = ''; // Pulisce il contenuto precedente

        // Sezione della domanda principale
        const questionMain = document.createElement('div');
        questionMain.className = 'question-main';

        const mainQuestion = document.createElement('div');
        mainQuestion.className = 'main-question';
        mainQuestion.textContent = d.question[1]; // Protezione XSS

        const subMessage = document.createElement('div');
        subMessage.className = 'sub-message';
        subMessage.textContent = 'Ora indica quale risposta pensi sia scritta da un umano:';

        questionMain.appendChild(mainQuestion);
        questionMain.appendChild(subMessage);
        chatView.appendChild(questionMain);

        // Sezione delle risposte
        const answersGrid = document.createElement('div');
        answersGrid.className = 'answers-grid';

        for (let i = 0; i < 4; i++) {
            const answer = answers[i];

            const form = document.createElement('form');
            form.action = "/get_tab_content/ask";
            form.method = "GET";

            const button = document.createElement('button');
            button.type = "submit";
            button.className = answer ? "answer-cell" : "answer-cell disabled";

            const title = document.createElement('div');
            title.className = 'answer-title';
            title.textContent = `Risposta ${i + 1}`;

            const text = document.createElement('div');
            text.className = 'answer-text';

            if (!answer) {
                text.classList.add('pending');
                const em = document.createElement('em');
                em.textContent = 'In attesa...';
                text.appendChild(em);
            } else {
                text.textContent = answer[1]; // Protezione XSS

                // Imposta l'onclick
                if (answer[2] !== -1) {
                    button.onclick = () => {
                        sendHuman(answer[2], d.question[0]);
                        showCustomPopup('+10 punti, era la risposta di un utente!');
                    };
                } else {
                    button.onclick = () => {
                        sendHuman(answer[2], d.question[0]);
                        showCustomPopup('Purtroppo era una risposta data da IA');
                    };
                }
            }

            button.appendChild(title);
            button.appendChild(text);
            form.appendChild(button);
            answersGrid.appendChild(form);
        }

        chatView.appendChild(answersGrid);
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