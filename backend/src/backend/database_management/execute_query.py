import mariadb

def execute_query_ask(connection:mariadb.Connection,query:str, params: list = None) -> list[list]:
    """Esegue una query di selezione sul database MariaDB.

    Questa funzione esegue la query fornita sulla connessione specificata in input e
    restituisce i risultati come lista di liste, dove la prima
    lista contiene i nomi delle colonne. In caso di errore durante l'esecuzione
    della query restituisce None.

    Args:
        connection (mariadb.Connection): L'oggetto di connessione al database MariaDB.
        query (str): La query SQL di richiesta (tendenzialmente una select) da eseguire.

    Returns:
        list[list]: Una lista di liste contenente i risultati della query, con la prima lista
                         che rappresenta le intestazioni delle colonne, le successive contengono 
                         i dati. Restituisce None se la query non è di interrogazione.
    """
    
    if query.startswith(("insert","remove","update")):
        return None
    try:
        cursor:mariadb.Cursor = connection.cursor()
        #esecuzione query, che salva i risultati in "result"
        if params:
            cursor.execute(query, params) # Esecuzione della query con parametri
        else:
            cursor.execute(query) # Esecuzione della query senza parametri 
        result=cursor.fetchall()
        colonne=[desc[0] for desc in cursor.description] #recupera i nomi degli attributi e li salva in "colonne"
        final=[] #inserimento in "final" dei dati di "colonne" e "result"
        final.append(colonne)
        for tupla in result:
            final.append(tupla)
    except mariadb.Error as e:
        print(f"Errore durante l'esecuzione della query: {e}")
        raise
    finally:
        if cursor:  # Verifica se il cursore è stato creato e lo chiude
            cursor.close()
    return final

def execute_query_modify(connection:mariadb.Connection,query:str, params: list = None) -> str:
    """Esegue una query di aggiunta, modifica o eliminazione sul database MariaDB.

    Esegue la query fornita sulla connessione specificata e restituisce una stringa 
    "ok" in caso di successo. Se si verifica un errore di integrità a causa di una voce 
    duplicata, restituisce la stringa "duplicato". In altri casi di errore durante l'esecuzione 
    della query esegue il rollback dell'operazione e restituisce la stringa "not ok".

    Args:
        connection (mariadb.Connection): L'oggetto di connessione al database MariaDB.
        query (str): La query SQL di modifica (tendenzialmente insert, delete o update) da eseguire.

    Returns:
        str: "ok" se la query è eseguita con successo, "duplicato" se si verifica
             un errore di chiave duplicata, altrimenti None se la query non è di modifica.
    """

    if query.startswith(("select")):
        return None
    
    results="ok"
    try:
        cursor:mariadb.Cursor = connection.cursor()
        if params:
            cursor.execute(query, params) # Esecuzione della query con parametri
        else:
            cursor.execute(query) # Esecuzione della query senza parametri 
    except mariadb.Error as e:
        print(f"Errore durante l'esecuzione della query: {e}")
        raise
    finally:
        if cursor:  # Verifica se il cursore è stato creato
            cursor.close()
    return results