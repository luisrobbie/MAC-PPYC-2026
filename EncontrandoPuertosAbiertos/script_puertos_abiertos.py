import socket
import threading
import queue

cola_procesos=queue.Queue()
semaforo= threading.Semaphore(100)

def probar_puertos(): 
	while not cola_procesos.empty():
		try:
			puerto, pagina= cola_procesos.get_nowait()
		except: 
			queue.Empty()
			break
		with semaforo:
			try:
				with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
					s.settimeout(1.5)
					result = s.connect_ex((pagina, puerto))
				if result==0:
					print (f"Puerto {puerto} abierto para la pagina {pagina}\n")
					with open("PuertosAbiertos.txt", "a") as f:
						f.write (f"Puerto {puerto} abierto para la pagina {pagina}\n")
			except:
				pass

if __name__ == "__main__":
	paginas_web=["google.com", "scanme.nmap.org", "testphp.vulnweb.com", "example.com"]
	#paginas_web=[ "192.168.1.254", "127.0.0.0"]
	
	for puerto in range (10000):
		for pagina in paginas_web:
			cola_procesos.put((puerto,pagina))

	hilos=[]

	for _ in range(100):
		hilo = threading.Thread(target=probar_puertos,)
		hilo.start()
		hilos.append(hilo)


	for hilo in hilos:
		hilo.join()

	print ("Puertos escaneados terminado")
