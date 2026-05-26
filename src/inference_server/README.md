# AI-Lawyer Inference Server — API для интеграции

---

## 1. Базовая информация


| Параметр          | Значение                                                                           |
| ----------------- | ---------------------------------------------------------------------------------- |
| Базовый префикс   | `/api/chat`                                                                        |
| Контракт ответов  | `application/json` (или `application/x-ndjson` для стрима)                         |
| Кодировка         | UTF-8                                                                              |
| CORS              | Открыт для всех (`*`)                                                              |
| Аутентификация    | **Нет** (предполагается, что инференс-сервер закрыт внутренним gateway / бэкендом) |
| Порт по умолчанию | `8000`                                                                             |


Если сервер развёрнут в общем `docker-compose.yaml` проекта — по умолчанию доступен по `http://inference-server:8000` из других контейнеров, либо `http://localhost:8000` снаружи (если проброшен порт).

---

## 2. Архитектура и список агентов

Сервер маршрутизирует запросы между тремя агентами:


| `agent_type` (path)       | Алиасы                         | Что делает                                                                                                                                                    |
| ------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `claims_agent`            | `claims`, `claim`              | Генерирует **исковые заявления** и **досудебные претензии** (DOCX). Имеет интерактивную intake-сессию — может попросить у пользователя дополнительные данные. |
| `general_questions_agent` | `general`, `general_questions` | Универсальный диалоговый агент: отвечает на любые вопросы текстом. Никаких документов не создаёт. Поддерживает контекстную память.                            |
| `router_agent`            | `router`                       | Сам классификатор. Прямой вызов нужен редко (для отладки).                                                                                                    |


В норме фронт **не выбирает агента** — используется `/invoke` или `/invoke/stream`, и сервер сам выбирает агента через router. Прямой вызов `/invoke/{agent_type}` нужен, когда:

- бэк хочет принудительно указать тип документа (`request_metadata.document_type`);
- бэк хочет получить ответ конкретно от general/claims, минуя router-классификатор;
- идёт отладка.

---

## 3. Сводка эндпоинтов


| Метод  | Путь                                   | Назначение                                 |
| ------ | -------------------------------------- | ------------------------------------------ |
| `GET`  | `/api/chat/health`                     | Health check                               |
| `POST` | `/api/chat/chat_name`                  | Сгенерировать имя для диалога              |
| `POST` | `/api/chat/invoke`                     | Основной эндпоинт диалога (без стрима)     |
| `POST` | `/api/chat/invoke/{agent_type}`        | Прямой вызов агента (без стрима)           |
| `POST` | `/api/chat/invoke/stream`              | Стриминговый аналог `/invoke` (NDJSON)     |
| `POST` | `/api/chat/invoke/{agent_type}/stream` | Стриминговый аналог `/invoke/{agent_type}` |


---

## 4. Сессии и `thread_id`

`thread_id: str` — обязательное поле почти везде. Это **идентификатор диалога** в инференс-сервере.

- Каждый `thread_id` имеет своё долговременное состояние:
  - история сообщений `general_questions_agent` (включая саммари-память);
  - частично заполненные поля `claims_agent` (когда пользователю не хватило данных и сервер ждёт уточнений).
- Один и тот же `thread_id` подразумевает **один и тот же диалог**. Сменился — новая сессия.
- Формат произвольный (UUID, цифровой ID на бэке — что угодно), главное — **стабильность в рамках диалога**.
- Стандартная стратегия на бэке: 1 диалог в БД = 1 `thread_id` на инференс.

---

## 5. Эндпоинт `/health`

```http
GET /api/chat/health
```

**Ответ:**

```json
{
  "status": "ok",
  "service": "AI-Lawyer Inference Server",
  "timestamp": "2026-05-25T12:34:56.789012"
}
```

Используйте для liveness/readiness-проб.

---

## 6. Эндпоинт `/chat_name` (имя диалога)

```http
POST /api/chat/chat_name
Content-Type: application/json

{
  "raw_input": "...первое сообщение пользователя...",
  "thread_id": "abc-123"
}
```


| Поле        | Тип   | Обязательно | Описание                                                                                     |
| ----------- | ----- | ----------- | -------------------------------------------------------------------------------------------- |
| `raw_input` | `str` | да          | Текст, по которому сгенерировать название. Обычно — первое сообщение пользователя в диалоге. |
| `thread_id` | `str` | да          | Эхо: вернётся в ответе как `thread_id`. На состояние диалога не влияет.                      |


**Ответ `ChatNameResponse`:**

```json
{
  "thread_id": "abc-123",
  "chat_name": "Возврат денег за бракованный товар",
  "latency_ms": 740,
  "input_tokens": 86,
  "output_tokens": 12,
  "total_tokens": 98,
  "run_id": "019e5f...",
  "trace_id": "019e5f...",
  "process_name": "llm_service"
}
```

Поля токенов и `run_id`/`trace_id` — для логирования/трассировки. Сам функционал даёт только `chat_name`.

Когда вызывать: рекомендуется один раз после первого пользовательского сообщения в диалоге.

---

## 7. Эндпоинт `/invoke` (без стрима)

```http
POST /api/chat/invoke
Content-Type: application/json

{
  "raw_input": "Составь иск к ООО Ромашка о возврате 200 000 руб.",
  "thread_id": "abc-123",
  "user_metadata": {
    "user_id": "u-42"
  }
}
```

### `ChatRequest`


| Поле            | Тип              | Обязательно        | Описание                                    |
| --------------- | ---------------- | ------------------ | ------------------------------------------- |
| `raw_input`     | `str`            | да                 | Сообщение пользователя. Произвольный текст. |
| `thread_id`     | `str`            | да                 | См. §4.                                     |
| `user_metadata` | `dict[str, Any]` | нет (default `{}`) | См. §10.                                    |


> Тело строго проверяется: лишние ключи запрещены (`extra="forbid"` в pydantic).

### `ChatResponse`

```json
{
  "reply": "...",
  "document_comment": "",
  "handled_by_agent": true,
  "document_created": false,
  "is_error": false,
  "latency_ms": 1730,
  "input_tokens": 1797,
  "output_tokens": 367,
  "total_tokens": 2164,
  "run_id": "019e5fd1-...",
  "trace_id": "019e5fd1-...",
  "process_name": "general_questions_agent"
}
```


| Поле                                                          | Тип    | Описание                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `reply`                                                       | `str`  | Основной канал ответа. **Если `document_created=false`** — это текст сообщения ассистента (его и надо показать пользователю). **Если `document_created=true`** — это абсолютный путь к DOCX-файлу (см. §11); текстовое сообщение в этом случае приходит в `document_comment`.                                                    |
| `document_comment`                                            | `str`  | Сопроводительное сообщение ассистента к сгенерированному документу: «готово, дальше можно сделать …». Это **обычное сообщение пользователю**, не системный статус — рендерить как новый пузырь от ассистента, а сгенерированный DOCX прикладывать к нему. Пустая строка во всех случаях, кроме claims с `document_created=true`. |
| `handled_by_agent`                                            | `bool` | `true`, если запрос обработан агентом. `false` при ошибках маршрутизации.                                                                                                                                                                                                                                                        |
| `document_created`                                            | `bool` | `true`, если по итогам этого запроса создан DOCX. Тогда `reply` содержит путь, а `document_comment` — текст к нему.                                                                                                                                                                                                              |
| `is_error`                                                    | `bool` | `true`, если внутри ответа описана ошибка.                                                                                                                                                                                                                                                                                       |
| `latency_ms`, `input_tokens`, `output_tokens`, `total_tokens` | `int`  | Метрики выполнения.                                                                                                                                                                                                                                                                                                              |
| `run_id`, `trace_id`                                          | `str`  | Идентификаторы LangSmith-трассировки (опционально для логирования).                                                                                                                                                                                                                                                              |
| `process_name`                                                | `str`  | Имя агента, который обработал запрос: `claims_agent`, `general_questions_agent`, `router_agent`, `llm_service`.                                                                                                                                                                                                                  |


### Матрица: что и куда положено


| Сценарий                                                 | `process_name`            | `document_created` | `is_error` | `reply`                              | `document_comment`                     |
| -------------------------------------------------------- | ------------------------- | ------------------ | ---------- | ------------------------------------ | -------------------------------------- |
| Общий вопрос                                             | `general_questions_agent` | `false`            | `false`    | Текст ответа LLM                     | `""`                                   |
| Прямой вызов `router_agent` (отладка)                    | `router_agent`            | `false`            | `false`    | Строка `"Классификация: агент=…"`    | `""`                                   |
| Claims: данных хватает, **документ сгенерирован**        | `claims_agent`            | `true`             | `false`    | Абсолютный путь к DOCX               | Текст «документ готов, дальше можно …» |
| Claims: данных не хватает — сервер запрашивает уточнения | `claims_agent`            | `false`            | `false`    | Текст «Недостаточно данных: укажи …» | `""`                                   |
| Любая внутренняя ошибка                                  | (любой)                   | `false`            | `true`     | Текст ошибки                         | `""`                                   |


### Как обрабатывать `reply` и `document_comment` на бэке/фронте

```python
if resp.document_created:
    # 1) DOCX-файл по пути resp.reply кладём в чат вложением.
    attach_document_to_chat(path=resp.reply)
    # 2) Текст из document_comment показываем как обычное сообщение ассистента
    #    — это сопровождающий комментарий к документу.
    show_assistant_message(resp.document_comment)
else:
    # Документа нет — reply содержит текст ответа.
    show_assistant_message(resp.reply)
```

Иначе говоря: `**reply` — это всегда то, что главное в этом ответе** (текст или файл). Если ответ — файл, то `document_comment` — это сопровождающий текст к нему. Если ответ — текст, то `document_comment` всегда пустой и его не надо ни проверять, ни показывать.

### Поведенческие случаи

- **Общий вопрос**: router → `general_questions_agent`. `reply` = текст. `document_created=false`. `document_comment=""`.
- **Запрос на иск/претензию, данных хватает**: router → `claims_agent` → DOCX. `reply` = путь к файлу, `document_created=true`, `document_comment` = текст «что дальше» — оба показать пользователю (см. псевдокод выше).
- **Запрос на иск/претензию, данных не хватает**: router → `claims_agent` → возвращает текст «Недостаточно данных: …». `document_created=false`. Бэку важно показать этот текст пользователю и не сбрасывать `thread_id` — следующий ответ пользователя будет «дополнением».
- **Дополнение данных в открытой claims-сессии**: тот же `/invoke` с тем же `thread_id`. Сервер сам поймёт.

---

## 8. Эндпоинт `/invoke/{agent_type}` (прямой вызов)

```http
POST /api/chat/invoke/claims_agent
Content-Type: application/json

{
  "raw_input": "Истец: ИП Иванов И.И., ответчик: ООО Ромашка, долг 200 000 руб.",
  "thread_id": "abc-123",
  "user_metadata": { "user_id": "u-42" },
  "request_metadata": { "document_type": "complaint" }
}
```

`agent_type` (в path) — один из:
`claims_agent` | `claim` | `claims` | `general_questions_agent` | `general_questions` | `general` | `router_agent` | `router`.

При неизвестном значении вернётся `400 Bad Request`.

### `ChatAgentRequest`


| Поле               | Тип              | Обязательно        | Описание                |
| ------------------ | ---------------- | ------------------ | ----------------------- |
| `raw_input`        | `str`            | да                 | Сообщение пользователя. |
| `thread_id`        | `str`            | да                 | См. §4.                 |
| `user_metadata`    | `dict[str, Any]` | нет (default `{}`) | См. §10.                |
| `request_metadata` | `dict[str, Any]` | нет (default `{}`) | См. §10.                |


**Ответ** — тот же `ChatResponse`, что у `/invoke`.

Используйте этот эндпоинт, когда нужно **гарантированно** обратиться к конкретному агенту, не зависеть от классификатора, и/или передать `request_metadata`.

### 8.1. Как правильно работать с `claims_agent`

`claims_agent` — один агент, который умеет генерировать **два типа документов**: исковое заявление (`document_type="lawsuit"`) и досудебную претензию (`document_type="complaint"`). Различия только во внутренних промптах, проверке полей и шапке итогового DOCX — граф и intake-сессия общие.

**Главное правило:** через `/invoke` (без `agent_type` в пути) тип документа определяет router-агент, и поле `request_metadata` не нужно. Через `/invoke/claims_agent` router пропускается — и тогда **тип документа обязательно задавать вручную** через `request_metadata.document_type`. Если поле не передать, агент по умолчанию сделает исковое заявление (`"lawsuit"`).


| Ситуация                                                           | Что передавать                                                                                                                                                                      |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Пользователь в чате просит «составь иск/претензию»                 | `POST /api/chat/invoke` или `…/invoke/stream`. Поле `request_metadata` не нужно — router сам определит документ.                                                                    |
| Фронт нажал кнопку «Составить **исковое заявление**»               | `POST /api/chat/invoke/claims_agent` с `"request_metadata": {"document_type": "lawsuit"}`.                                                                                          |
| Фронт нажал кнопку «Составить **досудебную претензию**»            | `POST /api/chat/invoke/claims_agent` с `"request_metadata": {"document_type": "complaint"}`.                                                                                        |
| Пользователь в открытой claims-сессии присылает уточнения по полям | Тот же `/invoke` (или `/invoke/claims_agent`) с тем же `thread_id`. `document_type` менять **нельзя** — он зафиксирован при первом запросе и хранится в state до завершения задачи. |


**Поведение агента:**

- Если данных хватает — сразу собирается DOCX. В `ChatResponse.reply` приходит путь к файлу, `document_created=true`, в `document_comment` — сопроводительное сообщение «что готово и что дальше», которое фронт показывает как обычное сообщение ассистента (и прикладывает к нему скачанный DOCX).
- Если данных не хватает — в `reply` приходит текст «Недостаточно данных: …», `document_created=false`. Бэк должен показать этот текст пользователю и **сохранить `thread_id`** — следующий запрос с тем же `thread_id` будет автоматически воспринят как дополнение полей.
- Если пользователь явно сменил тему (например, прислал «забудь, давай по другой теме»), сервер сам сбросит открытую сессию и заново классифицирует запрос.

**Что нельзя:**

- Менять `document_type` посреди уже идущей claims-сессии — он игнорируется до завершения текущей задачи.
- Запускать два параллельных запроса с одним `thread_id` в claims — будут гонки состояния.

---

## 9. Стриминговые эндпоинты

```http
POST /api/chat/invoke/stream
POST /api/chat/invoke/{agent_type}/stream
```

Тело запроса — то же, что у не-стрим вариантов (`ChatRequest` или `ChatAgentRequest`).

**Ответ:**

- `Content-Type: application/x-ndjson`
- Заголовки `X-Accel-Buffering: no`, `Cache-Control: no-cache` — для прозрачности через Nginx и пр.
- Тело — поток строк, каждая строка — отдельный JSON-объект (NDJSON, разделитель `\n`).

### Типы событий

#### 9.1. `progress` — промежуточное событие

```json
{
  "type": "progress",
  "stage": "answer",
  "content": "Кусок текста ответа",
  "document_type": null
}
```


| Поле            | Значение                                                                                                                                                                                                                                                                                                  |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `stage`         | `"answer"` — токены ответа `general_questions_agent`. `"pre_generation"` — короткий **системный статус** `claims_agent` «приступаю к генерации». `"document_comment"` — обычное **сообщение ассистента** от `claims_agent` к сгенерированному DOCX (путь к самому файлу приходит позже в `result.reply`). |
| `content`       | Текст события (кусок ответа, статус-сообщение или сопроводительный комментарий к документу).                                                                                                                                                                                                              |
| `document_type` | `"lawsuit"` / `"complaint"` для claims, `null` для general.                                                                                                                                                                                                                                               |


**Поведение по агентам и стадиям:**

- `general_questions_agent`, `stage="answer"` — приходит **много** маленьких `progress`-событий. Конкатенировать `content` в одно сообщение ассистента (эффект «печатания»).
- `claims_agent`, `stage="pre_generation"` — приходит **одно** короткое событие. Это системный статус: лучше рендерить как отдельный системный пузырь / индикатор «работаю над документом», а не как сообщение от ассистента.
- `claims_agent`, `stage="document_comment"` — это обычное сообщение от ассистента к сгенерированному документу. Рекомендуется создать новый пузырь от ассистента и приложить к нему DOCX (путь придёт в `result.reply`, см. ниже).

#### 9.2. `result` — финальное событие

```json
{
  "type": "result",
  "reply": "...",
  "document_comment": "",
  "handled_by_agent": true,
  "document_created": false,
  "is_error": false,
  "error": null,
  "latency_ms": 2628,
  "input_tokens": 1791,
  "output_tokens": 272,
  "total_tokens": 2063,
  "run_id": "...",
  "trace_id": "...",
  "process_name": "general_questions_agent"
}
```

Поля по смыслу те же, что у `ChatResponse` (см. §7) — включая ту же матрицу `reply` ↔ `document_comment`, — плюс `error`. Финальное событие приходит **всегда** в самом конце — даже если до этого был стрим.

> `document_comment` в `result` дублирует то, что уже было прислано в `progress.stage="document_comment"` (на случай, если фронт не накапливал стрим). Если фронт собирал стрим, поле можно проигнорировать.

#### 9.3. `error` — критическая ошибка

```json
{"type": "error", "message": "Описание ошибки"}
```

Приходит при сбое внутри инференса. Может прийти как единственное событие или после нескольких progress (если сбой случился по ходу). Гарантии «после error не будет result» — нет: фронт должен **завершать сессию по `result` или `error`, что придёт раньше**.

### Минимальный псевдокод обработки стрима

```text
on event:
  if event.type == "progress":
    if event.stage == "answer":
      # general_questions_agent: токен ответа, дописать в текущий пузырь ассистента.
      append_to_current_assistant_message(event.content)
    elif event.stage == "pre_generation":
      # claims_agent: системный статус «приступаю к генерации»,
      # отдельный системный пузырь / индикатор.
      show_status_bubble(event.content)
    elif event.stage == "document_comment":
      # claims_agent: обычное сообщение ассистента после генерации DOCX.
      # Завести новый пузырь ассистента (или дописывать токены, если они придут чанками).
      append_to_new_assistant_message(event.content)

  elif event.type == "result":
    # Финальное событие. Если document_created — путь к DOCX лежит в reply,
    # прикладываем файл к последнему пузырю ассистента (тому, в который
    # копили document_comment). Если document_created == false — reply
    # это просто текст ответа, его уже могли собрать из progress.
    if event.document_created:
      attach_document_to_last_assistant_message(path=event.reply)
    finalize_message(event)                        # сохранить токены и т.д.
    close_stream()

  elif event.type == "error":
    show_error(event.message)
    close_stream()
```

### Важно про сеть и прокси

- На стороне **Nginx / reverse-proxy** обязательно отключите буферизацию для этих маршрутов: `proxy_buffering off;` (или `X-Accel-Buffering: no` сервер уже отдаёт). Без этого стрим придёт «одной телеграммой».
- Браузерный `EventSource` тут **не подходит** (он умеет только GET и SSE-формат). Используйте `fetch` + `ReadableStream` (см. §13).

---

## 10. `user_metadata` и `request_metadata`

### `user_metadata`

Назначение: данные о **пользователе и сессии**. Прокидываются сквозь весь пайплайн.


| Ключ         | Тип   | Используется    | Описание                                                                                                                                              |
| ------------ | ----- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `user_id`    | `str` | `claims_agent`  | Используется в путях сохраняемых DOCX: `${GENERATED_DOCX_PATH}/{user_id}/{thread_id}/<имя_файла>.docx`. Если не передан — подставится `unknown_user`. |
| любые другие | любые | (опц., будущее) | Можно класть `email`, `username`, `language` и т.п. Не используются сейчас, но не отбрасываются — пройдут через граф в trace-метаданных.              |


**Рекомендация:** всегда передавайте `user_id`, чтобы файлы пользователей не складывались в общий каталог `unknown_user`.

### `request_metadata`

Назначение: параметры **конкретного вызова агента**, нужные только этому запросу. Используется только в `/invoke/{agent_type}` (на `/invoke` без `agent_type` не передаётся — там роутер сам решает).


| Ключ            | Тип                             | Агент          | Описание                                                                       |
| --------------- | ------------------------------- | -------------- | ------------------------------------------------------------------------------ |
| `document_type` | `"lawsuit"` или `"complaint"` | `claims_agent` | Принудительно задаёт тип документа. Если пропущено — по умолчанию `"lawsuit"`. |


Пример для прямого вызова claims с претензией:

```json
{
  "raw_input": "Подготовь претензию к продавцу за бракованный товар, сумма 50 000 руб.",
  "thread_id": "abc-123",
  "user_metadata": { "user_id": "u-42" },
  "request_metadata": { "document_type": "complaint" }
}
```

---

## 11. Документы DOCX

Когда `claims_agent` успешно создаёт документ:

- `reply` в `ChatResponse` (или в `result`-событии стрима) содержит **абсолютный путь к файлу** внутри контейнера инференс-сервера:
  ```
  /generated_docx/{user_id}/{thread_id}/{кратко}_{дата_время}.docx
  ```
- Путь к корню документов задаётся переменной окружения `GENERATED_DOCX_PATH` (по умолчанию `/generated_docx`).
- Файлы сохраняются на **общий volume**, смонтированный одновременно в `inference-server` и `backend`. Бэк может читать их напрямую с того же пути.
- `document_created=true`, `process_name="claims_agent"`, `document_comment` — сопроводительный текст ассистента «документ готов, дальше можно сделать …» (см. §7, матрицу и псевдокод обработки).

Если генерация не удалась (DOCX не сохранился): `document_created=false`, `reply` содержит человекочитаемое описание ошибки.

---

## 12. Сценарии использования (для разработчика)

### 12.1. Стандартный диалог с router (без стрима)

1. Пользователь пишет сообщение.
2. Бэк (или фронт) дёргает `POST /api/chat/invoke` с `thread_id` и сообщением.
3. Сервер сам выбирает агента и отвечает.
4. Бэк сохраняет `reply` (если документ — путь к DOCX) и токены в БД.
5. Следующее сообщение — снова `/invoke` с тем же `thread_id`. Сессия восстанавливается автоматически.

### 12.2. Диалог со стримом (UX как у ChatGPT)

1. Тот же сценарий, но фронт открывает поток к `POST /api/chat/invoke/stream`.
2. Фронт читает NDJSON-события и:
  - копит токены `progress.stage=answer` в один пузырь сообщения;
  - на `progress.stage="pre_generation"` показывает короткий системный пузырь / индикатор (это статус, не сообщение от ассистента);
  - на `progress.stage="document_comment"` заводит новый пузырь ассистента и копит в него текст; после прихода `result` прикладывает к этому пузырю DOCX по пути из `result.reply`;
  - на `result` фиксирует финальный ответ и метрики, закрывает соединение.

### 12.3. Принудительное создание иска или претензии

1. Фронт показывает кнопку «Составить претензию».
2. Бэк дёргает `POST /api/chat/invoke/claims_agent` (или `…/claims_agent/stream`) с:
  ```json
   {
     "raw_input": "<всё, что пользователь надиктовал>",
     "thread_id": "<id>",
     "user_metadata": { "user_id": "<id>" },
     "request_metadata": { "document_type": "complaint" }
   }
  ```
3. Если данных не хватило — пользователю показывается текст из `reply`, диалог продолжается обычными `/invoke` с тем же `thread_id`.

### 12.4. Название диалога

1. Сразу после первого пользовательского сообщения фронт/бэк делает один вызов `/api/chat/chat_name`.
2. Полученный `chat_name` сохраняется в БД для отображения в списке диалогов.

---

## 13. Примеры

### 13.1. curl — обычный invoke

```bash
curl -X POST http://localhost:8000/api/chat/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "raw_input": "Объясни, что такое срок исковой давности",
    "thread_id": "demo-1",
    "user_metadata": {"user_id": "u-1"}
  }'
```

### 13.2. curl — invoke/stream (NDJSON)

`-N` обязателен — отключает буферизацию у curl:

```bash
curl -N -X POST http://localhost:8000/api/chat/invoke/stream \
  -H "Content-Type: application/json" \
  -d '{
    "raw_input": "Составь иск к ООО Ромашка о возврате 200 000 руб.",
    "thread_id": "demo-2",
    "user_metadata": {"user_id": "u-1"}
  }'
```

### 13.3. JavaScript (fetch + ReadableStream)

```javascript
async function streamChat({ rawInput, threadId, userId }) {
  const resp = await fetch("http://localhost:8000/api/chat/invoke/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      raw_input: rawInput,
      thread_id: threadId,
      user_metadata: { user_id: userId },
    }),
  });
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();        // последняя — возможно, неполная
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      onEvent(event);
    }
  }
}

function onEvent(event) {
  switch (event.type) {
    case "progress":
      if (event.stage === "answer") appendAssistantText(event.content);
      else                          showStatusBubble(event.content);
      break;
    case "result":
      finalizeMessage(event);
      break;
    case "error":
      showError(event.message);
      break;
  }
}
```

### 13.4. Python (httpx)

```python
import httpx, json

async def stream_chat(raw_input: str, thread_id: str, user_id: str):
    payload = {
        "raw_input": raw_input,
        "thread_id": thread_id,
        "user_metadata": {"user_id": user_id},
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/chat/invoke/stream",
            json=payload,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if event["type"] == "progress" and event["stage"] == "answer":
                    print(event["content"], end="", flush=True)
                elif event["type"] == "result":
                    print(f"\n[done] {event['process_name']}")
                elif event["type"] == "error":
                    print(f"\n[error] {event['message']}")
                    break
```

### 13.5. Получение имени диалога

```bash
curl -X POST http://localhost:8000/api/chat/chat_name \
  -H "Content-Type: application/json" \
  -d '{
    "raw_input": "Хочу взыскать с продавца возврат за товар",
    "thread_id": "demo-3"
  }'
```

---

## 14. Обработка ошибок

### 14.1. HTTP-коды


| Код                         | Когда                                                                                                                                           |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `200 OK`                    | Успех (для `/invoke/...` сам факт ответа). Для стрим-эндпоинтов **сама ошибка приходит как событие `error` внутри потока**, статус всё ещё 200. |
| `400 Bad Request`           | Неизвестный `agent_type` в path.                                                                                                                |
| `422 Unprocessable Content` | Невалидный JSON / нарушение схемы (`extra="forbid"`, отсутствие `raw_input`/`thread_id`).                                                       |
| `500 Internal Server Error` | Внутренняя ошибка (например, при `/invoke` упал агент). Тело: `{"detail": "..."}`.                                                              |


### 14.2. Логические ошибки внутри 200

Сервер старается возвращать `200 OK` с осмысленным телом, даже если по сути ничего не сгенерировал:

- `is_error: true`, `reply` содержит описание;
- `document_created: false`;
- `process_name` подскажет, кто среагировал на запрос.

Бэк должен учитывать это поле перед сохранением ответа в БД.

---

## 15. Переменные окружения (резюме того, что важно для интеграции)


| Переменная            | Значение по умолчанию | Зачем фронту/бэку знать                                                                                                                                 |
| --------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GENERATED_DOCX_PATH` | `/generated_docx`     | Корень сохранения DOCX. Полный путь к файлу возвращается в `reply` после успешной генерации. Бэк должен иметь доступ к этой же директории через volume. |
| `LOGS_DIR`            | `/logs`               | Куда инференс пишет логи. Бэку обычно не нужно.                                                                                                         |
| `MODE`                | `DEBUG`               | Если `DEBUG` — логи только в stdout. Иначе — также в `LOGS_FILE` внутри `LOGS_DIR`.                                                                     |
| `SBER_AUTH`           | —                     | Авторизация GigaChat. На стороне инференса.                                                                                                             |


Подробнее см. `.env.example` в корне репозитория.

---

## 16. Контракт «коротко на одном листе»

```text
POST /api/chat/invoke                 → ChatResponse
POST /api/chat/invoke/{agent_type}    → ChatResponse
POST /api/chat/invoke/stream          → NDJSON {progress | result | error}
POST /api/chat/invoke/{agent_type}/stream
                                      → NDJSON {progress | result | error}
POST /api/chat/chat_name              → ChatNameResponse
GET  /api/chat/health                 → {status, service, timestamp}

ChatRequest      { raw_input*, thread_id*, user_metadata? }
ChatAgentRequest { raw_input*, thread_id*, user_metadata?, request_metadata? }

user_metadata    { user_id?: str, ... }
request_metadata { document_type?: "lawsuit"|"complaint", ... }   # claims_agent

ChatResponse {
  reply,                  # текст (если document_created=false) ИЛИ путь к DOCX (если document_created=true)
  document_comment,       # сопроводительное сообщение к DOCX; "" во всех остальных случаях
  handled_by_agent,
  document_created,
  is_error,
  latency_ms, input_tokens, output_tokens, total_tokens,
  run_id, trace_id, process_name
}

stream event progress { type:"progress", stage:"answer"|"pre_generation"|"document_comment",
                        content, document_type? }
stream event result   { type:"result", ...ChatResponse поля..., error? }
stream event error    { type:"error", message }
```

