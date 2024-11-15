# Codeguardai

# How to run it?

`docker-compose up --build`  - crea la imagen de la base de datos de postgresql y la imagen de flask

# ¿Cómo hacer un deploy en Fly.io?

1. Crear una cuenta en Fly.io y elegir el tier de development.
2. Debes ingresar una tarjeta de crédito. No te van a cobrar por usar el modo development.
3. Copiar el repo codeguardai e ir al branch de cloud.
4. Instalar fly terminal  `https://fly.io/docs/flyctl/install/`
5. Crear una base de datos con postgres con `fly postgres create` después te aparecerá un prompt y escribes el nombre de `codeguardai-db`
6. Hacer el primer deploy de la aplicación con `fly launch`
7. Ligar la base de datos con la aplicación `fly postgres attach codeguardai-db`. Esto creará en automático el secret para conectar la aplicación con la base de datos.
8. Establecer los secret values con `fly secrets set OPENAI_API_KEY="VALORDELALLAVE"` y `fly secrets set FLASK_SECRET_KEY="123456"`