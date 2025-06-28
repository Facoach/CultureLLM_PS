
        const tabEndpoints = {
            'ask': '/get_tab_content/ask',
            'leaderboard': '/get_tab_content/leaderboard',
            'answer': '/get_tab_content/answer'
        };

        function handlePostSubmitEvent(event) {
            handleFormSubmission(event, 'POST');
        }

        function handleGetSubmitEvent(event) {
            handleFormSubmission(event, 'GET');
        }

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

            //POPUP
            // Seleziona tutti i form con la classe 'answer-form'
            const forms = document.querySelectorAll('.answer-form');

            forms.forEach(form => {
                form.addEventListener('submit', function(event) {
                    // Impedisci l'invio immediato del form
                    event.preventDefault();

                    // Mostra il popup
                    alert("Grazie per aver risposto!\nDei punti verranno assegnati a chi ha scritto la risposta, se è stata opera di un'umano. Riesci ad indovinare quale delle risposte era data da una persona?");

                    // Invia il form dopo un breve ritardo (opzionale, per dare tempo all'utente di vedere il popup)
                    // Puoi regolare il ritardo (in millisecondi) o rimuoverlo se preferisci che il form venga inviato subito dopo il popup
                    setTimeout(() => {
                        this.submit();
                    }, 100); // 100 millisecondi di ritardo
                });
            });
            //FINE POPUP
        
        }

        async function handleFormSubmission(event, method) {
            event.preventDefault();

            const form = event.target;
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true; // Disabilita il pulsante
            }

            const tabContentContainer = form.closest('.tab-content');
            if (tabContentContainer) {
                tabContentContainer.innerHTML = 'Esecuzione in corso...';
            }

            const url = form.action;
            let options = { method: method };

            if (method === 'POST') {
                options.body = new FormData(form);
            }

            try {
                const response = await fetch(url, options);

                if (!response.ok) {
                    let detail = "Errore durante l'operazione.";
                    try {
                        const errorJson = await response.json();
                        if (errorJson && errorJson.detail) {
                            detail = errorJson.detail;
                        }
                    } catch (e) {
                        // Ignora se la risposta non è JSON
                    }
                    throw new Error(`HTTP error! status: ${response.status} - ${detail}`);
                }

                const updatedHtml = await response.text();

                if (tabContentContainer) {
                    tabContentContainer.innerHTML = updatedHtml;
                    initializeTabForms();
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

        async function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));

            document.getElementById(`${tabName}-content`).classList.add('active');
            document.querySelector(`.tab-button[data-tab-name="${tabName}"]`).classList.add('active');
        }

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
                    contentContainer.innerHTML = htmlContent;
                } catch (error) {
                    console.error(`Errore nel caricamento del tab ${tabName}:`, error);
                    contentContainer.innerHTML = `<p style="color: red;">Errore nel caricamento del tab ${tabName}.</p>`;
                }
            }
            initializeTabForms();
            showTab('ask'); // Mostra il primo tab 'Ask' di default
        }

        // Questo è il blocco mancante che gestisce i click sui pulsanti dei tab
        document.addEventListener('DOMContentLoaded', () => {
            // Carica tutti i contenuti dei tab quando la pagina è pronta
            loadAllTabContents();

            // Aggiungi listener per i click sui pulsanti dei tab
            document.querySelectorAll('.tab-button').forEach(button => {
                button.addEventListener('click', () => {
                    const tabName = button.dataset.tabName;
                    showTab(tabName); // Mostra il tab cliccato
                });
            });
            
        });

        
        /*-------------------------*/
        /*-------------------------*/
        function loadValidate(questionId, checked) {
            fetch('/validate', {
                method: 'POST',
                headers: {'Content-Type':'application/x-www-form-urlencoded'},
                body: `questionid=${questionId}`
            })
            .then(r => r.json())
            .then(d => {
                const answers = d.answers || [];
                // Costruisci la matrice risposte (max 4, sempre 2x2)
                const answerBlocks = [];
                for(let i=0; i<4; i++) {
                    const answer = answers[i];
                    // Controlla se la domanda è stata già valutata o se non c'è risposta,
                    // in tal caso i bottoni sono disattivati
                    if (checked == 1 || !answer) {
                        answerBlocks.push(`
                            <div class="answer-cell disabled">
                                <div class="answer-title">Risposta ${i+1}</div>
                                <div class="answer-text pending">${answer ? answer[1] : "<em>In attesa...</em>"}</div>
                            </div>
                        `);
                    }
                    // Se la risposta è ancora da valutare e ha ricevuto risposta
                    // i bottoni sono attivi
                    else {
                        answerBlocks.push(`
                            <button class="answer-cell" onclick="sendBest(${d.question[0]},${answer[0]})">
                                <div class="answer-title">Risposta ${i + 1}</div>
                                <div class="answer-text">${answer[1]}</div>
                            </button>
                        `);
                    }
                }
                // Se è stata valutata mostra solo 
                if(checked == 1) {
                    document.getElementById('chat-view').innerHTML = `
                        <div class="question-main">
                            <div class="main-question">${d.question[1]}</div>
                        </div>
                        <div class="best-answer-block">
                            <div class="best-title">Risposta migliore</div>
                            <div class="best-answer">${answers.length > 0 ? answers[0][1] : "<em>Non disponibile</em>"}</div>
                        </div>
                    `;
                } else if(answers.length === 0) {
                    // IN ATTESA RISPOSTE
                    document.getElementById('chat-view').innerHTML = `
                        <div class="question-main">
                            <div class="main-question">${d.question[1]}</div>
                        </div>
                        <div class="waiting-message">
                            <span>In attesa delle risposte...</span>
                        </div>
                    `;
                } else {
                    // SCELTA RISPOSTA MIGLIORE
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
        
        // Dopo aver scelto la migliore, scegli la risposta umana (stesso layout)
        function sendBest(questionId, answerId) {
            fetch('/best', {
                method: 'POST',
                headers: {'Content-Type':'application/x-www-form-urlencoded'},
                body: `questionid=${questionId}&answerid=${answerId}`
            })
            .then(r => r.json())
            .then(d => {
                const answers = d.answers || [];
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
                        answerBlocks.push(`
                            <button class="answer-cell" onclick="sendHuman(${answer[2]}, ${d.question[0]})">
                                <div class="answer-title">Risposta ${i+1}</div>
                                <div class="answer-text">${answer[1]}</div>
                            </button>
                        `);
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
            })
            .catch(err => console.error(err));
        }
        
        // Dopo la scelta "umana", mostra solo il messaggio di conferma
        function sendHuman(humanId, questionId) {
            fetch('/human', {
                method: 'POST',
                headers: {'Content-Type':'application/x-www-form-urlencoded'},
                body: `human=${humanId}&questionid=${questionId}`
            })
            .then(r => r.json())
            .then(d => {
                document.getElementById('chat-view').innerHTML = `
                    <div class="waiting-message">
                        ${d.message}
                    </div>
                `;
            })
            .catch(err => console.error(err));
        }
        
        function checkNewAnswers() {
            fetch('/check_new_answers')
            .then(res => res.json())
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
        /*-------------------------*/

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
                leaderboardContainer.innerHTML = htmlContent;
                // Una volta aggiornato il contenuto, se ci fossero form al suo interno,
                // è buona pratica reinizializzare i loro listener.
                initializeTabForms();
            } catch (error) {
                console.error("Errore durante l'aggiornamento della leaderboard:", error);
                // Opzionale: mostrare un messaggio di errore all'utente
                // leaderboardContainer.innerHTML = `<p style="color: red;">Errore nel caricamento della classifica.</p>`;
            }
        }

        setInterval(refreshLeaderboard, 5000);