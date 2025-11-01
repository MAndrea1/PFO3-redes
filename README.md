# PFO 3: Rediseño como Sistema Distribuido (Cliente-Servidor) 
Micaela Andrea Higa

## Diagrama teórico de un sistema distribuido.

![Sistema distribuido](docs\diagrama.png)

En este diagrama podemos observar:  
o Clientes (móviles, web).   
o Balanceador de carga (Nginx/HAProxy).   
o Servidores workers (cada uno con su pool de hilos).  
o Cola de mensajes (RabbitMQ) para comunicación entre servidores.  
o Almacenamiento distribuido (PostgreSQL, S3).  



## Implementación simple de un sistema distribuido

Se utilizó Python para simular un sistema distribuido con estas características:  

o Un servidor que reciba tareas por socket y las distribuya a workers.   
o Un cliente que envíe tareas y reciba resultados  


Elementos:

1. **Balanceador de Carga (Load Balancer)** - `src/load_balancer.py`
   - Servidor front-end que recibe tareas de clientes
   - Distribuye tareas entre workers disponibles usando round-robin
   - Devuelve resultados a los clientes

2. **Worker** - `src/worker.py`
   - Servidor back-end que procesa tareas
   - Se conecta al balanceador y se registra como disponible
   - Procesa tareas y devuelve resultados

3. **Cliente** - `src/client.py`
   - Aplicación que envía tareas al balanceador
   - Recibe resultados del procesamiento


## Instalación

1. Crear y activar un entorno virtual:

```bash
# Windows PowerShell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python3.12 -m venv .venv
source .venv/bin/activate
```


## Uso

### 1. Iniciar el Balanceador de Carga

En una terminal, ejecutar:

```bash
python src/load_balancer.py
```

La terminal debería mostrar:
```
[LOAD BALANCER] Iniciado en localhost
[LOAD BALANCER] Escuchando clientes en puerto 8888
[LOAD BALANCER] Escuchando workers en puerto 8889
```

### 2. Iniciar Workers

En **múltiples terminales** (una por cada worker), ejecutar:

```bash
python src/worker.py
```

Cada terminal muestra:
```
[WORKER worker_xxxx] Conectado al balanceador en localhost:8889
[WORKER worker_xxxx] Registrado como disponible
[WORKER worker_xxxx] Registro confirmado por balanceador
[WORKER worker_xxxx] Listo para procesar tareas
```

**Recomendación**: Inicia al menos 2-3 workers para ver la distribución de carga.

### 3. Enviar Tareas desde el Cliente

En otra terminal, ejecutar:

```bash
python src/client.py
```

El cliente enviará tareas de ejemplo y mostrará los resultados.

### Ejemplo de Salida

**Balanceador:**
```
[LOAD BALANCER] Worker conectado desde ('127.0.0.1', xxxx)
[LOAD BALANCER] Worker registrado: worker_abc123 desde ('127.0.0.1', xxxx)
[LOAD BALANCER] Cliente conectado desde ('127.0.0.1', xxxx)
[LOAD BALANCER] Tarea recibida: task_xyz789 de ('127.0.0.1', xxxx)
[LOAD BALANCER] Tarea task_xyz789 asignada a worker worker_abc123
[LOAD BALANCER] Resultado recibido para tarea task_xyz789
[LOAD BALANCER] Resultado enviado al cliente para tarea task_xyz789
```

**Worker:**
```
[WORKER worker_abc123] Tarea recibida: task_xyz789, datos: 1,2,3,4,5
[WORKER worker_abc123] Tarea procesada: suma de [1, 2, 3, 4, 5] = 15
[WORKER worker_abc123] Resultado enviado para tarea task_xyz789
```

**Cliente:**
```
[CLIENT] Conectado al balanceador en localhost:8888
[CLIENT] Enviando tarea task_xyz789: 1,2,3,4,5
[CLIENT] Resultado recibido para tarea task_xyz789: 15
```

## Protocolo de Comunicación

### Cliente ↔ Balanceador

- **Cliente → Balanceador**: `TASK|task_id|task_data`
- **Balanceador → Cliente**: `RESULT|task_id|result_data`

### Balanceador ↔ Worker

**Fase de Registro:**
- **Worker → Balanceador**: `REGISTER|worker_id`
- **Balanceador → Worker**: `ACK|worker_id`

**Fase de Procesamiento:**
- **Balanceador → Worker**: `ASSIGN_TASK|task_id|task_data`
- **Worker → Balanceador**: `TASK_RESULT|task_id|result_data`

## Funcionalidad de Ejemplo

El sistema procesa tareas de suma de números:
- **Formato de entrada**: `"1,2,3,4,5"` (lista de números separados por coma)
- **Formato de salida**: `"15"` (suma de los números)

Se pueden modificar `src/worker.py` en el método `process_task()` para implementar otros ejemplos.


## Estructura del Proyecto

```
PFO3/
├── src/
│   ├── __init__.py
│   ├── load_balancer.py      # Balanceador de carga
│   ├── worker.py             # Procesador de tareas
│   └── client.py             # Cliente que envía tareas
├── tests/
│   ├── __init__.py
│   └── (tests a implementar)
├── requirements.txt
└── README.md
```
