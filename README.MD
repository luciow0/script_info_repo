Pasos para que el script sea funcional:

[1] Instalar las siguientes dependencias: 

-> pip install requests rich

[2] Crear el archivo toke.txt y escribir en la primera linea: 

-> GITHUB_TOKEN = {tu token de github para acceder a la API}

* Este archivo sera ignorado por defecto, revisar .gitignore
* Procure no exponer su llave de acceso personal, se recomienda añadirla 
* como variable de entorno de manera local y modificar el script para que solo usted tenga acceso

[3] Ejecutar el script en Powershell o CMD con: 

-> python repo_health.py <usuario> <repositorio>