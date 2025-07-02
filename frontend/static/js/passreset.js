window.addEventListener('pagehide', function(event){
    if(!event.persisted){
        const logoutEndpoint = '/logout'; // Sostituisci con il tuo endpoint di logout effettivo
    const data = JSON.stringify({ message: 'User logging out' });

    // Controlla se sendBeacon è supportato dal browser
    if (navigator.sendBeacon) {
      navigator.sendBeacon(logoutEndpoint, data);
      console.log('Logout beacon sent.');
    } else {
      // Fallback per browser che non supportano sendBeacon (meno affidabile)
      console.warn('navigator.sendBeacon not supported. Attempting less reliable logout.');
      // fetch (potrebbe non essere completato)
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