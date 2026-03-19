import time
import random
import requests
import threading
from bs4 import BeautifulSoup
import queue
from sqlalchemy import create_engine, text
from datetime import datetime

cola_procesos = queue.Queue()
cola_inserciones=queue.Queue()

#Conexión con la base de datos
user="postgres"
password="supersecret"
host="localhost"
port="5432"
database="postgres"


def get_connection(user, password, host, port, database):
    return create_engine(url="postgresql+psycopg2://{0}:{1}@{2}:{3}/{4}".format(user, password, host, port, database))

def insert_price(symbol, precio):
    engine = get_connection(user, password, host, port, database)

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO INVERSIONES(symbol, precio, fecha_registro) VALUES (:s,:p,NOW())"),
            {"s": symbol, "p": precio}
        )

#def insert_price(symbol, precio):
 #   with get_connection(user, password, host   , port, database).connect() as connector:
  #      connector.execute(text(f"INSERT INTO INVERSIONES(symbol, price, register_date) values ('{symbol}', '{precio}', NOW())"))
   #     connector.commit()

def obtener_precio_stock():
    while not cola_procesos.empty():
        try:
            symbol = cola_procesos.get_nowait()
        except queue.Empty:
            break
        URL = f"https://finance.yahoo.com/quote/{symbol}"

        headers = {
            "User-Agent": "MiProyecto/1.0"
        }
        
        while True:
            time.sleep(30 * random.random())
            response = requests.get(URL, headers=headers,)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                valor = soup.find("span", {"data-testid": "qsp-price"})
                if valor:
                    precio = valor.text.strip()
                    insert_price(symbol, precio)
                else:
                    precio = "Privado"
                break
            else:
                continue
        print(f"La accion {symbol} cuesta: {precio}")
        #VALUES= "VALUES" + {symbol} + ", " + {precio} + "," + "now()" + ","
        cola_procesos.task_done()


#def insertar_registros_datos():
 #   while not cola_inserciones.empty():
  #      try:
   #         symbol = cola_inserciones.get_nowait()
    #    except queue.Empty:
     #       break
      # 
       #while True:

if __name__ == "__main__":   
    start=time.time()
                
    with open("./lista_sp500.txt", "r") as f:
        lista_symbolos = eval(f.read())
    threads = []
    
    for symbol in lista_symbolos:
        cola_procesos.put(symbol)
    
    for _ in range(8):
        t = threading.Thread(target = obtener_precio_stock)
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()

    print(f"El tiempo que tardo es: {time.time()-start}")
