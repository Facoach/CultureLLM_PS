// Funzione per copiare il codice di invito negli appunti
function copyInviteCode() {
    const code = document.getElementById('invite-code').innerText;
    navigator.clipboard.writeText(code);
}

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