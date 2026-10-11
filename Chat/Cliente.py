import socket
import sys
import threading

# Configuración del socket con IPv4 y TCP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Configuración de la dirección IP y el puerto del servidor al que se conectará el cliente
# 'localhost' para probar en el mismo Mac del servidor.
# Para conectarse por Hamachi, cambiarla por la IP de Hamachi del servidor
server_address = ('localhost', 12345)

# Evento para avisarle al hilo receptor que el cierre es voluntario (exit o Ctrl+C)
saliendo = threading.Event()

def recibir_mensajes(sock):
    # Hilo receptor: imprime todo lo que llegue del servidor, en cualquier momento
    while True:
        try:
            data = sock.recv(1024)
        except OSError:
            break  # El socket se cerró desde este cliente

        if not data:
            if not saliendo.is_set():
                print("\nEl servidor cerró la conexión. Presiona Enter para salir.")
            break

        # Los mensajes del servidor ya traen '\n'
        print(data.decode('utf-8'), end='')

print(f"Conectando al servidor en {server_address[0]}:{server_address[1]}...")
try:
    client_socket.connect(server_address)
except ConnectionRefusedError:
    print("No se pudo conectar al servidor. ¿Está en ejecución?")
    client_socket.close()
    sys.exit(1)

# Crear el hilo receptor (daemon=True: termina junto con el programa)
receiver_thread = threading.Thread(target=recibir_mensajes, args=(client_socket,), daemon=True)
receiver_thread.start()

# El primer mensaje que se envía es el nombre, no un mensaje del chat
nombre_enviado = False

try:
    while True:
        # Leer un mensaje del usuario
        message = input()

        # Si el servidor se cayó, el hilo receptor ya terminó
        if not receiver_thread.is_alive():
            break

        if not message.strip():
            continue  # No enviar mensajes vacíos

        if message.lower() == 'exit':
            saliendo.set()
            print("Desconectando del servidor...")

        # Enviar el mensaje al servidor (con '\n' para marcar el fin del mensaje)
        client_socket.sendall((message + '\n').encode('utf-8'))

        if message.lower() == 'exit':
            break

        if nombre_enviado:
            # El servidor ya no nos reenvía nuestro mensaje: se borra la línea
            # que dejó input() (\033[F sube una línea, \033[K la limpia)
            # y se muestra en el historial como "Tú: mensaje"
            print(f"\033[F\033[KTú: {message}")
        else:
            nombre_enviado = True

except KeyboardInterrupt:
    saliendo.set()
    print("\nDesconectando del servidor...")

except (BrokenPipeError, ConnectionResetError):
    print("Se perdió la conexión con el servidor.")

finally:
    # Cerrar el socket del cliente
    client_socket.close()
    print("Conexión cerrada.")