from mariadb import Connection, Cursor, Error
from typing import Optional, List


def execute_query_ask(connection:Connection, query:str, params: list = None) -> Optional[List[list]]:
    """
    Esegue una query di selezione sul database MariaDB
    usando i prepared statement.
    La esegue sulla connessione specificata in input e
    restituisce i risultati come lista di liste, dove la prima lista 
    contiene i nomi delle colonne, le successive i dati. 
    Se la query non è di selezione, restituisce None.
    """
    
    if query.startswith(("insert","remove","update")):
        return None
    
    # Esegue la query (con o senza parametri), recupera i nomi degli attributi (li salva in "colonne")
    # e crea la lista da restituire (come sopra descritta)
    try:
        cursor:Cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        result=cursor.fetchall()
        colonne=[desc[0] for desc in cursor.description]
        final=[]
        final.append(colonne)
        for tupla in result:
            final.append(tupla)

    except Error as e:
        print(f"Errore durante l'esecuzione della query: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
    return final


def execute_query_modify(connection:Connection,query:str, params: list = None) -> Optional[str]:
    """
    Esegue una query di aggiunta, modifica o eliminazione sul database MariaDB
    usando i prepared statement.
    La esegue sulla connessione specificata e restituisce "ok" in caso di 
    successo, None se la query non è di modifica.
    """

    if query.startswith(("select")):
        return None
    
    results="ok"
    # Esegue la query (con o senza parametri)
    try:
        cursor:Cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
    except Error as e:
        print(f"Errore durante l'esecuzione della query: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
    return results