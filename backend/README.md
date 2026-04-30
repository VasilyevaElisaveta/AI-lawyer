# Backend

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
Для локального запуска данные поля не являются обязательными, так как предусмотрена автоподстановка значений, но для создания пользователя с правами администратора поля <code>admin</code> должны быть заполнены.
## Запуск

Команды для запуска:
- <code>uv sync</code> — установка зависимостей;
- <code>uv run app/main.py</code> — запуск приложения.

Во время запуска приложения можно передать следующие дополнительные параметры:
- <code>--sync</code> — запуск синхронной базы данных sqlite3;
- <code>--reset</code> — сброс и создание всех таблиц базы данных;
- <code>--detail</code> — вывод запросов к базе данных;
- <code>--temp</code> — хранение локальной базы данных sqlite3 во временной папке, которая после завершения работы приложения очищается.

## Работа
<code>http://localhost:8000/api/v1/docs</code> — ссылка на Swagger UI.