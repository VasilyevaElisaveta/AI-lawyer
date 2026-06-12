# AI-lawyer
ИИ-Юрист — интеллектуальный помощник для составления исков, претензий и расчёта госпошлины на основе GigaChat
## Подготовка
Необходимо создать <code>.env</code> файл и заполнить следующие поля:
```
# password hash
HASH=
ALGORITHM=
ACCESS_TOKEN_EXPIRE_MINUTES=
REFRESH_TOKEN_EXPIRE_MINUTES=

# admin
admin_username=
admin_email=
admin_password=

admin_name=
admin_surname=

# database
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=

# Значения storage_path и GENERATED_DOCX_PATH должны быть одинаковыми  

# backend storage / logs (внутри контейнера backend)
storage_path=
logs_path=

# shared inference paths (внутри контейнера inference-server)
GENERATED_DOCX_PATH=
LOGS_DIR=
LOGS_FILE=

# Redis для checkpoint'ов LangGraph в inference-server (при MODE!=DEBUG)
REDIS_URL=

# inference-server параметры
SBER_AUTH=
LANGSMITH_TRACING=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=
HASH_LENGTH=
LLM_MODEL=
LLM_GENERATION_MODEL=
GIGACHAT_SCOPE=
MODE=

# ip адрес сервера, где будет производиться деплой, чтобы можно было указать в allow_origins
deploy_server_ip=
```
## Запуск
Команды для запуска локального запуска:
-  <code>docker compose up -d --build</code> — запуск приложения в первый раз;
-  <code>docker compose up -d</code> — последующий запуск;
-  <code>docker compose down</code> — завершение работы.

Команда для запуска на сервере:
- <code>docker compose -f docker-compose.deploy.yaml up -d</code> — запуск всего приложения.
## Работа
<code>http://\<your ip address\></code> — ссылка на сайт;
<code>http://127.0.0.1/api/v1/docs</code> — ссылка на Swagger UI.
