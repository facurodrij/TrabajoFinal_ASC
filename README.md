# Sistema para gestión de Reservas, Eventos, Socios y Pagos de un Club Deportivo

## Descripción
Este sistema ha sido construido para la aprobación de la materia Trabajo Final y finalización de la carrera de Analista
en Sistemas de Computación de la Universidad Nacional de Misiones. 

El sistema permite la gestión de reservas de canchas de fútbol, eventos, socios y pagos de un club deportivo. Se integra
con la plataforma de MercadoPago para la realización de pagos online.

## Requisitos
Para poder ejecutar el sistema, se debe contar con los siguientes requisitos:
- Python 3.8 o superior

## Instalación
Para instalar el sistema, se debe clonar el repositorio y luego ejecutar los siguientes comandos:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## Ejecución
Antes de ejecutar el sistema recomiendo cargar los datos de configuración que se encuentran en los directorios
fixtures/ dentro de cada aplicación. Para ello, ejecutar los siguientes comandos:
```
python manage.py loaddata core/fixtures/*.json eventos/fixtures/*.json parameters/fixtures/*.json socios/fixtures/*.json reservas/fixtures/*.json
```
Opcionalmente, se puede cargar un conjuntos de datos de prueba que se encuentran en el directorio dumps/ dentro de cada
aplicación. Para ello, ejecutar los siguientes comandos:
```
python manage.py loaddata core/dumps/*.json eventos/dumps/*.json socios/dumps/*.json reservas/dumps/*.json
```

Para ejecutar el sistema, se debe ejecutar el siguiente comando:
```
python manage.py runserver
```
