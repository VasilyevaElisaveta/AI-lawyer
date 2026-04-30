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

# docs storage
storage_path= 
 
#logs
logs_path=
```
## Запуск

Команды для запуска:
- <code>docker compose up -d --build</code> — запуск приложения в первый раз;
- <code>docker compose up -d</code> — последующий запуск;
- <code>docker compose  down</code> — завершение работы.

## Работа
<code>http://127.0.0.1/api/v1/docs</code> — ссылка на Swagger UI.