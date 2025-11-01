"""
Worker - Servidor Back-end de Procesamiento

Este componente actúa como un servidor back-end que procesa tareas. Representa
un nodo de procesamiento en un sistema distribuido que ejecuta trabajo pesado
mientras el balanceador coordina la distribución de carga.

RESPONSABILIDADES:
1. Conectarse al balanceador de carga
2. Registrarse como worker disponible
3. Recibir tareas asignadas por el balanceador
4. Procesar las tareas (cálculos, simulaciones, etc.)
5. Enviar resultados de vuelta al balanceador
"""

import socket
from typing import Optional
from uuid import uuid4


class Worker:
    """
    Worker que procesa tareas recibidas del balanceador.
    
    Simula un servidor back-end que se conecta al balanceador, se registra,
    y procesa tareas distribuidas, devolviendo resultados al balanceador.
    """
    
    def __init__(
        self,
        balancer_host: str = "localhost",
        balancer_port: int = 8889,
        worker_id: Optional[str] = None
    ) -> None:
        """
        Inicializa el worker.
        
        Args:
            balancer_host: Dirección del balanceador de carga
            balancer_port: Puerto del balanceador para workers
            worker_id: ID único del worker (se genera si no se proporciona)
        """
        # ROL: Configuración de conexión al balanceador
        # El worker debe conocer la dirección del balanceador front-end
        self.balancer_host = balancer_host
        self.balancer_port = balancer_port
        self.worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        
        # ROL: Estado del worker
        self.running = False
    
    def connect(self) -> bool:
        """
        Conecta el worker al balanceador.
        
        ROL: Establecimiento de conexión con servidor front-end
        El worker se conecta al balanceador y se registra como disponible
        para procesar tareas.
        
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            # ROL: Conexión al balanceador
            # Crear socket y conectar al puerto de workers del balanceador
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.balancer_host, self.balancer_port))
            print(f"[WORKER {self.worker_id}] Conectado al balanceador en {self.balancer_host}:{self.balancer_port}")
            
            # ROL: Registro de disponibilidad
            # El worker se registra enviando su ID al balanceador
            register_message = f"REGISTER|{self.worker_id}\n"
            self.socket.send(register_message.encode('utf-8'))
            print(f"[WORKER {self.worker_id}] Registrado como disponible")
            
            # ROL: Confirmación de registro
            # Esperamos ACK del balanceador confirmando que estamos registrados
            response = self.socket.recv(1024).decode('utf-8')
            parts = response.strip().split('|')
            
            if len(parts) == 2 and parts[0] == 'ACK':
                print(f"[WORKER {self.worker_id}] Registro confirmado por balanceador")
                return True
            else:
                print(f"[WORKER {self.worker_id}] Error en registro: {response}")
                return False
                
        except (ConnectionRefusedError, OSError) as e:
            print(f"[WORKER {self.worker_id}] Error al conectar: {e}")
            return False
    
    def process_task(self, task_data: str) -> str:
        """
        Procesa una tarea y devuelve el resultado.
        
        ROL: Ejecución de trabajo pesado
        Este método contiene la lógica de procesamiento real. En este ejemplo,
        procesa una lista de números y devuelve su suma.
        
        Args:
            task_data: Datos de la tarea a procesar (formato: "1,2,3,4,5")
            
        Returns:
            Resultado del procesamiento (formato: "15")
        """
        # ROL: Procesamiento de tarea
        # En un sistema real, aquí se ejecutaría el trabajo pesado:
        # - Cálculos matemáticos complejos
        # - Simulaciones
        # - Procesamiento de imágenes
        # - Consultas a bases de datos
        # etc.
        
        try:
            # Ejemplo: procesar suma de números
            # Formato esperado: "1,2,3,4,5"
            numbers = [int(x.strip()) for x in task_data.split(',')]
            result = sum(numbers)
            print(f"[WORKER {self.worker_id}] Tarea procesada: suma de {numbers} = {result}")
            return str(result)
        except (ValueError, AttributeError) as e:
            # ROL: Manejo de errores en procesamiento
            # Si la tarea no puede ser procesada, devolvemos un error
            error_msg = f"ERROR: {str(e)}"
            print(f"[WORKER {self.worker_id}] Error procesando tarea: {e}")
            return error_msg
    
    def start(self) -> None:
        """
        Inicia el worker y comienza a procesar tareas.
        
        ROL: Bucle principal del servidor back-end
        El worker entra en un bucle donde espera tareas, las procesa,
        y devuelve resultados al balanceador.
        """
        if not self.connect():
            return
        
        self.running = True
        print(f"[WORKER {self.worker_id}] Listo para procesar tareas")
        
        try:
            while self.running:
                # ROL: Recepción de tareas asignadas
                # El balanceador envía tareas en formato: ASSIGN_TASK|task_id|task_data
                data = self.socket.recv(1024).decode('utf-8')
                
                if not data:
                    break
                
                parts = data.strip().split('|', 2)
                if len(parts) != 3 or parts[0] != 'ASSIGN_TASK':
                    print(f"[WORKER {self.worker_id}] Formato de mensaje inválido: {data}")
                    continue
                
                _, task_id, task_data = parts
                print(f"[WORKER {self.worker_id}] Tarea recibida: {task_id}, datos: {task_data}")
                
                # ROL: Procesamiento de la tarea
                # Ejecutamos el trabajo pesado
                result_data = self.process_task(task_data)
                
                # ROL: Envío de resultado al balanceador
                # Devolvemos el resultado en formato: TASK_RESULT|task_id|result_data
                result_message = f"TASK_RESULT|{task_id}|{result_data}\n"
                self.socket.send(result_message.encode('utf-8'))
                print(f"[WORKER {self.worker_id}] Resultado enviado para tarea {task_id}")
                
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[WORKER {self.worker_id}] Conexión cerrada: {e}")
        finally:
            self.socket.close()
            print(f"[WORKER {self.worker_id}] Desconectado")
    
    def stop(self) -> None:
        """Detiene el worker."""
        self.running = False


def main() -> None:
    """
    Función principal para ejecutar el worker.
    
    ROL: Punto de entrada del servidor back-end
    Inicia un worker que se conectará al balanceador y procesará tareas.
    """
    worker = Worker()
    try:
        worker.start()
    except KeyboardInterrupt:
        print("\n[WORKER] Deteniendo worker...")
        worker.stop()


if __name__ == "__main__":
    main()

