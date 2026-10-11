import socket
import threading

# Configuración del socket con IPv4 y TCP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Configuración de la dirección IP y el puerto del servidor
# La dirección 0.0.0.0 permite que el servidor escuche en todas las interfaces de red
# La IP de Hamachi para que se conecten los clientes de la red virtual de Hamachi
server_address = ('0.0.0.0', 12345)

# Configuración para reutilizar la dirección y el puerto
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Vinculación del socket a la dirección y puerto especificados
server_socket.bind(server_address)
print(f"Servidor escuchando en {server_address[0]}:{server_address[1]}")

# Poner el socket en modo de escucha para aceptar conexiones entrantes
server_socket.listen(1)

# Lista compartida con los sockets de los clientes que ya están en el chat
clients = []
# Candado que protege la lista: solo un hilo a la vez puede leerla o modificarla
clients_lock = threading.Lock()

def broadcast(message, sender=None):
    # Enviar un mensaje a todos los clientes del chat (sección crítica)
    # Si se indica sender, ese cliente no recibe el mensaje (ya sabe lo que envió)
    with clients_lock:
        disconnected = []
        for client in clients:
            if client is sender:
                continue
            try:
                client.sendall(message.encode('utf-8'))
            except OSError:
                # Si falla con uno, se anota y se sigue con los demás
                disconnected.append(client)

        # Se quitan después del recorrido (no se borra mientras se recorre)
        for client in disconnected:
            clients.remove(client)

def handle_client(client_socket, client_address):
    name = ""
    joined = False  # Indica si el cliente llegó a entrar a la lista del chat
    try:
        # Enviar un mensaje de bienvenida al cliente
        welcome_message = "¡Bienvenido al chat! Escribe 'exit' para desconectarte.\n"
        client_socket.sendall(welcome_message.encode('utf-8'))

        # Pedir el nombre antes de dejar chatear (se repite mientras llegue vacío)
        while not name:
            name_message = "Escribe tu nombre:\n"
            client_socket.sendall(name_message.encode('utf-8'))

            data = client_socket.recv(1024)
            if not data:
                print(f"Cliente {client_address} se desconectó antes de dar su nombre.")
                return  # El finally cierra el socket

            name = data.decode('utf-8').strip()

        if name.lower() == 'exit':
            print(f"Cliente {client_address} salió antes de dar su nombre.")
            return

        # Saludar al cliente por su nombre
        greeting = f"Hola, {name}. Ya puedes escribir.\n"
        client_socket.sendall(greeting.encode('utf-8'))

        # Agregar al cliente a la lista compartida (sección crítica)
        with clients_lock:
            clients.append(client_socket)
        joined = True

        print(f"{name} se unió al chat desde {client_address}")
        broadcast(f"*** {name} se unió al chat ***\n", client_socket)

        while True:
            # Recibir datos del cliente
            data = client_socket.recv(1024)
            if not data:
                print(f"{name} {client_address} se ha desconectado.")
                break  # El cliente se ha desconectado

            message = data.decode('utf-8').strip()

            if message.lower() == 'exit':
                print(f"{name} {client_address} se ha desconectado.")
                break

            print(f"{name}: {message}")

            # Enviar el mensaje a todos los clientes del chat, menos a quien lo escribió
            broadcast(f"{name}: {message}\n", client_socket)

    except Exception as e:
        print(f"Error al manejar al cliente {client_address}: {e}")

    finally:
        # Quitar al cliente de la lista (sección crítica)
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)

        # Cerrar el socket del cliente (una sola vez, cuando ya terminó)
        client_socket.close()

        # Anunciar la salida FUERA del with: broadcast toma el mismo candado
        # y tomarlo dos veces en el mismo hilo causaría un interbloqueo
        if joined:
            broadcast(f"*** {name} salió del chat ***\n")

# Escucha de conexiones entrantes
print("Servidor listo para recibir conexiones.")
try:
    while True:
        # Aceptar una conexión entrante
        client_socket, client_address = server_socket.accept()
        print(f"Conexión establecida con {client_address}")

        # Crear un hilo para manejar al cliente
        # daemon=True: el hilo termina junto con el programa principal
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True)
        client_thread.start()

except KeyboardInterrupt:
    print("\nServidor detenido.")

finally:
    server_socket.close()