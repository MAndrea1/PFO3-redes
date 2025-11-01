"""
Balanceador de Carga (Load Balancer) - Servidor Front-end

Este componente actúa como el punto de entrada del servidor. Su función es recibir
tareas de múltiples clientes y distribuirlas entre workers disponibles, simulando
un balanceador de carga real (similar a NGINX o HAProxy).

RESPONSABILIDADES:
1. Escuchar conexiones de clientes (puerto 8888)
2. Escuchar conexiones de workers (puerto 8889)
3. Registrar workers disponibles
4. Distribuir tareas usando algoritmo round-robin
5. Mantener mapeo de tareas a clientes para devolver resultados
6. Manejar desconexiones de workers y clientes
"""

import socket
import threading
import queue
from typing import Dict, Optional, Tuple
from uuid import uuid4


class LoadBalancer:
    """
    Balanceador de carga que distribuye tareas entre workers.
    
    Simula un servidor front-end que actúa como intermediario entre clientes
    y workers, distribuyendo la carga de trabajo de manera equilibrada.
    """
    
    def __init__(
        self,
        client_port: int = 8888,
        worker_port: int = 8889,
        host: str = "localhost"
    ) -> None:
        """
        Inicializa el balanceador de carga.
        
        Args:
            client_port: Puerto para escuchar conexiones de clientes
            worker_port: Puerto para escuchar conexiones de workers
            host: Dirección IP donde escuchar (default: localhost)
        """
        # ROL: Configuración del servidor front-end
        # El balanceador necesita dos puertos: uno para clientes y otro para workers
        self.client_port = client_port
        self.worker_port = worker_port
        self.host = host
        
        # ROL: Gestión de workers disponibles
        # Cola circular para implementar round-robin
        self.workers: queue.Queue[Tuple[socket.socket, str]] = queue.Queue()
        self.worker_lock = threading.Lock()
        
        # ROL: Mapeo de tareas a clientes
        # Necesitamos saber a qué cliente enviar cada resultado
        self.task_to_client: Dict[str, socket.socket] = {}
        self.task_lock = threading.Lock()
        
        # ROL: Control de ejecución
        self.running = False
        self.client_threads: list[threading.Thread] = []
        self.worker_threads: list[threading.Thread] = []
    
    def start(self) -> None:
        """
        Inicia el balanceador y comienza a escuchar conexiones.
        
        ROL: Inicialización del servidor front-end
        Crea dos sockets servidor (uno para clientes, otro para workers)
        y comienza a aceptar conexiones en hilos separados.
        """
        self.running = True
        
        # ROL: Servidor para clientes
        # Este socket recibe las tareas que los clientes quieren procesar
        client_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_server.bind((self.host, self.client_port))
        client_server.listen(5)
        
        # ROL: Servidor para workers
        # Este socket recibe los workers que quieren procesar tareas
        worker_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        worker_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        worker_server.bind((self.host, self.worker_port))
        worker_server.listen(5)
        
        print(f"[LOAD BALANCER] Iniciado en {self.host}")
        print(f"[LOAD BALANCER] Escuchando clientes en puerto {self.client_port}")
        print(f"[LOAD BALANCER] Escuchando workers en puerto {self.worker_port}")
        
        # ROL: Aceptación de conexiones
        # Cada tipo de conexión se maneja en un hilo dedicado
        client_thread = threading.Thread(
            target=self._accept_clients,
            args=(client_server,),
            daemon=True
        )
        worker_thread = threading.Thread(
            target=self._accept_workers,
            args=(worker_server,),
            daemon=True
        )
        
        client_thread.start()
        worker_thread.start()
        
        self.client_threads.append(client_thread)
        self.worker_threads.append(worker_thread)
        
        try:
            # Mantener el balanceador corriendo
            while self.running:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            print("\n[LOAD BALANCER] Deteniendo balanceador...")
            self.stop()
    
    def _accept_clients(self, server_socket: socket.socket) -> None:
        """
        Acepta conexiones entrantes de clientes.
        
        ROL: Manejo de conexiones de clientes
        Cada cliente que se conecta se maneja en un hilo separado para
        permitir múltiples clientes simultáneos.
        
        Args:
            server_socket: Socket servidor para clientes
        """
        while self.running:
            try:
                client_socket, address = server_socket.accept()
                print(f"[LOAD BALANCER] Cliente conectado desde {address}")
                
                # ROL: Manejo concurrente de clientes
                # Cada cliente tiene su propio hilo para procesar múltiples tareas
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                self.client_threads.append(client_thread)
            except OSError:
                if self.running:
                    break
    
    def _accept_workers(self, server_socket: socket.socket) -> None:
        """
        Acepta conexiones entrantes de workers.
        
        ROL: Registro de workers disponibles
        Cada worker que se conecta se registra en el pool de workers disponibles
        para procesar tareas.
        
        Args:
            server_socket: Socket servidor para workers
        """
        while self.running:
            try:
                worker_socket, address = server_socket.accept()
                print(f"[LOAD BALANCER] Worker conectado desde {address}")
                
                # ROL: Manejo de registro de workers
                # Cada worker tiene su propio hilo para manejar su registro
                worker_thread = threading.Thread(
                    target=self._handle_worker,
                    args=(worker_socket, address),
                    daemon=True
                )
                worker_thread.start()
                self.worker_threads.append(worker_thread)
            except OSError:
                if self.running:
                    break
    
    def _handle_client(
        self,
        client_socket: socket.socket,
        address: Tuple[str, int]
    ) -> None:
        """
        Maneja la comunicación con un cliente específico.
        
        ROL: Recepción de tareas y envío de resultados
        Este método recibe tareas del cliente, las distribuye a workers,
        y devuelve los resultados al cliente.
        
        Args:
            client_socket: Socket del cliente
            address: Dirección del cliente
        """
        try:
            while self.running:
                # ROL: Recepción de tareas del cliente
                # El formato esperado es: TASK|task_id|task_data
                data = client_socket.recv(1024).decode('utf-8')
                
                if not data:
                    break
                
                parts = data.strip().split('|', 2)
                if len(parts) != 3 or parts[0] != 'TASK':
                    print(f"[LOAD BALANCER] Formato de mensaje inválido: {data}")
                    continue
                
                _, task_id, task_data = parts
                print(f"[LOAD BALANCER] Tarea recibida: {task_id} de {address}")
                
                # ROL: Mapeo de tarea a cliente
                # Guardamos qué cliente envió esta tarea para poder enviarle el resultado
                with self.task_lock:
                    self.task_to_client[task_id] = client_socket
                
                # ROL: Distribución de tareas
                # Intentamos asignar la tarea a un worker disponible
                self._assign_task_to_worker(task_id, task_data)
                
        except (ConnectionResetError, BrokenPipeError, OSError):
            print(f"[LOAD BALANCER] Cliente {address} desconectado")
        finally:
            client_socket.close()
    
    def _handle_worker(
        self,
        worker_socket: socket.socket,
        address: Tuple[str, int]
    ) -> None:
        """
        Maneja la comunicación con un worker específico.
        
        ROL: Registro y gestión de workers
        Este método registra workers disponibles y recibe resultados de tareas
        procesadas, luego los envía de vuelta a los clientes correspondientes.
        
        Args:
            worker_socket: Socket del worker
            address: Dirección del worker
        """
        worker_id: Optional[str] = None
        
        try:
            # ROL: Registro de worker
            # El worker envía REGISTER|worker_id al conectarse
            data = worker_socket.recv(1024).decode('utf-8')
            
            if not data:
                return
            
            parts = data.strip().split('|')
            if len(parts) != 2 or parts[0] != 'REGISTER':
                print(f"[LOAD BALANCER] Formato de registro inválido: {data}")
                return
            
            worker_id = parts[1]
            print(f"[LOAD BALANCER] Worker registrado: {worker_id} desde {address}")
            
            # ROL: Confirmación de registro
            # Enviamos ACK para confirmar que el worker está registrado
            worker_socket.send(f"ACK|{worker_id}\n".encode('utf-8'))
            
            # ROL: Agregar worker al pool disponible
            # Ahora este worker puede recibir tareas para procesar
            with self.worker_lock:
                self.workers.put((worker_socket, worker_id))
            
            # ROL: Recepción de resultados de tareas
            # El worker procesará tareas y enviará resultados
            while self.running:
                data = worker_socket.recv(1024).decode('utf-8')
                
                if not data:
                    break
                
                parts = data.strip().split('|', 2)
                if len(parts) != 3 or parts[0] != 'TASK_RESULT':
                    continue
                
                _, task_id, result_data = parts
                print(f"[LOAD BALANCER] Resultado recibido para tarea {task_id}")
                
                # ROL: Envío de resultado al cliente
                # Buscamos qué cliente envió esta tarea y le enviamos el resultado
                self._send_result_to_client(task_id, result_data)
                
                # ROL: Devolver worker al pool
                # El worker terminó su tarea y está disponible para otra
                with self.worker_lock:
                    self.workers.put((worker_socket, worker_id))
                
        except (ConnectionResetError, BrokenPipeError, OSError):
            print(f"[LOAD BALANCER] Worker {worker_id} desconectado")
        finally:
            worker_socket.close()
            # Remover worker del pool si aún está ahí
            # (Nota: esto es simplificado, en producción se necesitaría más lógica)
    
    def _assign_task_to_worker(self, task_id: str, task_data: str) -> None:
        """
        Asigna una tarea a un worker disponible.
        
        ROL: Distribución de carga (Load Balancing)
        Implementa algoritmo round-robin: asigna tareas a workers en orden,
        distribuyendo la carga de manera equilibrada.
        
        Args:
            task_id: Identificador único de la tarea
            task_data: Datos de la tarea a procesar
        """
        # ROL: Selección de worker (round-robin)
        # Obtenemos el siguiente worker disponible de la cola
        try:
            worker_socket, worker_id = self.workers.get(timeout=5)
            
            # ROL: Asignación de tarea
            # Enviamos la tarea al worker en formato: ASSIGN_TASK|task_id|task_data
            message = f"ASSIGN_TASK|{task_id}|{task_data}\n"
            worker_socket.send(message.encode('utf-8'))
            print(f"[LOAD BALANCER] Tarea {task_id} asignada a worker {worker_id}")
            
        except queue.Empty:
            # ROL: Manejo de sobrecarga
            # Si no hay workers disponibles, la tarea espera
            # En producción, aquí se podría implementar una cola de tareas pendientes
            print(f"[LOAD BALANCER] No hay workers disponibles para tarea {task_id}")
            # Por simplicidad educativa, reintentamos después
            # En producción se usaría una cola de tareas pendientes
            threading.Timer(1.0, self._assign_task_to_worker, args=(task_id, task_data)).start()
    
    def _send_result_to_client(self, task_id: str, result_data: str) -> None:
        """
        Envía el resultado de una tarea al cliente que la solicitó.
        
        ROL: Devolución de resultados
        Busca el cliente que envió la tarea originalmente y le envía el resultado.
        
        Args:
            task_id: Identificador de la tarea completada
            result_data: Resultado del procesamiento
        """
        with self.task_lock:
            client_socket = self.task_to_client.pop(task_id, None)
        
        if client_socket:
            try:
                # ROL: Envío de resultado
                # Formato: RESULT|task_id|result_data
                message = f"RESULT|{task_id}|{result_data}\n"
                client_socket.send(message.encode('utf-8'))
                print(f"[LOAD BALANCER] Resultado enviado al cliente para tarea {task_id}")
            except (ConnectionResetError, BrokenPipeError, OSError):
                print(f"[LOAD BALANCER] No se pudo enviar resultado: cliente desconectado")
        else:
            print(f"[LOAD BALANCER] No se encontró cliente para tarea {task_id}")
    
    def stop(self) -> None:
        """Detiene el balanceador de carga."""
        self.running = False


def main() -> None:
    """
    Función principal para ejecutar el balanceador de carga.
    
    ROL: Punto de entrada del servidor front-end
    Inicia el balanceador que coordinará todas las comunicaciones.
    """
    balancer = LoadBalancer()
    balancer.start()


if __name__ == "__main__":
    main()

