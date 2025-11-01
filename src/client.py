"""
Cliente - Aplicación que Envía Tareas

Este componente actúa como el cliente de la aplicación. Representa el usuario
o aplicación que necesita que se procesen tareas en el servidor distribuido.

RESPONSABILIDADES:
1. Conectarse al balanceador de carga
2. Generar tareas con ID único
3. Enviar tareas al balanceador
4. Esperar y recibir resultados
5. Mostrar resultados al usuario
"""

import socket
from typing import Optional
from uuid import uuid4


class Client:
    """
    Cliente que envía tareas al balanceador y recibe resultados.
    
    Simula un usuario o aplicación que necesita procesar tareas en el
    servidor distribuido, enviando tareas al balanceador y recibiendo resultados.
    """
    
    def __init__(
        self,
        balancer_host: str = "localhost",
        balancer_port: int = 8888
    ) -> None:
        """
        Inicializa el cliente.
        
        Args:
            balancer_host: Dirección del balanceador de carga
            balancer_port: Puerto del balanceador para clientes
        """
        # ROL: Configuración de conexión al servidor
        # El cliente debe conocer la dirección del balanceador front-end
        self.balancer_host = balancer_host
        self.balancer_port = balancer_port
        self.socket: Optional[socket.socket] = None
    
    def connect(self) -> bool:
        """
        Conecta el cliente al balanceador.
        
        ROL: Establecimiento de conexión con servidor front-end
        El cliente se conecta al balanceador para poder enviar tareas.
        
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            # ROL: Conexión al balanceador
            # Crear socket y conectar al puerto de clientes del balanceador
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.balancer_host, self.balancer_port))
            print(f"[CLIENT] Conectado al balanceador en {self.balancer_host}:{self.balancer_port}")
            return True
        except (ConnectionRefusedError, OSError) as e:
            print(f"[CLIENT] Error al conectar: {e}")
            return False
    
    def send_task(self, task_data: str) -> Optional[str]:
        """
        Envía una tarea al balanceador y espera el resultado.
        
        ROL: Envío de tareas y recepción de resultados
        El cliente genera un ID único para la tarea, la envía al balanceador,
        y espera a recibir el resultado del procesamiento.
        
        Args:
            task_data: Datos de la tarea a procesar (ej: "1,2,3,4,5")
            
        Returns:
            Resultado del procesamiento o None si hubo error
        """
        if not self.socket:
            print("[CLIENT] No hay conexión establecida. Llame a connect() primero.")
            return None
        
        # ROL: Generación de ID único
        # Cada tarea necesita un ID único para poder rastrear el resultado
        task_id = f"task_{uuid4().hex[:8]}"
        print(f"[CLIENT] Enviando tarea {task_id}: {task_data}")
        
        try:
            # ROL: Envío de tarea al balanceador
            # Formato: TASK|task_id|task_data
            message = f"TASK|{task_id}|{task_data}\n"
            self.socket.send(message.encode('utf-8'))
            
            # ROL: Espera de resultado
            # El cliente espera a recibir el resultado del balanceador
            # Formato esperado: RESULT|task_id|result_data
            response = self.socket.recv(1024).decode('utf-8')
            parts = response.strip().split('|', 2)
            
            if len(parts) == 3 and parts[0] == 'RESULT':
                result_task_id, result_data = parts[1], parts[2]
                
                # ROL: Verificación de ID de tarea
                # Verificamos que el resultado corresponde a nuestra tarea
                if result_task_id == task_id:
                    print(f"[CLIENT] Resultado recibido para tarea {task_id}: {result_data}")
                    return result_data
                else:
                    print(f"[CLIENT] ID de tarea no coincide: esperado {task_id}, recibido {result_task_id}")
                    return None
            else:
                print(f"[CLIENT] Formato de respuesta inválido: {response}")
                return None
                
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[CLIENT] Error en comunicación: {e}")
            return None
    
    def disconnect(self) -> None:
        """Desconecta el cliente del balanceador."""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("[CLIENT] Desconectado")


def main() -> None:
    """
    Función principal para ejecutar el cliente.
    
    ROL: Punto de entrada de la aplicación cliente
    Ejemplo de uso del cliente que envía tareas y recibe resultados.
    """
    client = Client()
    
    if not client.connect():
        print("[CLIENT] No se pudo conectar al balanceador. Asegúrese de que esté corriendo.")
        return
    
    try:
        # Ejemplo de envío de múltiples tareas
        # ROL: Envío de tareas al servidor
        # Estas tareas serán distribuidas entre los workers disponibles
        
        tasks = [
            "1,2,3,4,5",        # Suma = 15
            "10,20,30",         # Suma = 60
            "100,200,300,400",  # Suma = 1000
        ]
        
        print("\n[CLIENT] Enviando tareas al servidor...")
        results = []
        
        for task_data in tasks:
            result = client.send_task(task_data)
            if result:
                results.append(result)
            print()  # Línea en blanco para legibilidad
        
        print("\n[CLIENT] Resumen de resultados:")
        for i, result in enumerate(results, 1):
            print(f"  Tarea {i}: {result}")
            
    except KeyboardInterrupt:
        print("\n[CLIENT] Interrumpido por usuario")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()

