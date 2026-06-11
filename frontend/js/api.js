/* API client — auto-refresh on 401, streaming support */
const api = (() => {
  let _refreshing = null;

  async function refreshTokens() {
    const rt = Auth.getRefresh();
    if (!rt) throw new Error('No refresh token');
    const res = await fetch(`${API}/user/refresh-tokens/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: rt }),
    });
    if (!res.ok) { Auth.clear(); throw new Error('Сессия истекла'); }
    const data = await res.json();
    Auth.save(data.access_token, data.refresh_token);
    return data.access_token;
  }

  function parseError(e) {
    if (!e) return 'Неизвестная ошибка';
    if (Array.isArray(e.detail)) {
      return e.detail.map(d => {
        const field = d.loc ? d.loc[d.loc.length - 1] : '';
        return field ? `${field}: ${d.msg}` : d.msg;
      }).join('\n');
    }
    if (typeof e.detail  === 'string') return e.detail;
    if (typeof e.message === 'string') return e.message;
    return JSON.stringify(e);
  }

  function authHeaders() {
    const token = Auth.getAccess();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function request(path, opts = {}, retry = true) {
    const headers = { ...authHeaders(), ...(opts.headers || {}) };
    if (opts.body && !(opts.body instanceof FormData) && typeof opts.body === 'object') {
      headers['Content-Type'] = 'application/json';
      opts = { ...opts, body: JSON.stringify(opts.body) };
    }
    const res = await fetch(`${API}${path}`, { ...opts, headers });

    if (res.status === 401 && retry) {
      if (!_refreshing) _refreshing = refreshTokens().finally(() => { _refreshing = null; });
      try { await _refreshing; } catch { Auth.clear(); throw new Error('Необходима авторизация'); }
      return request(path, opts, false);
    }
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { msg = parseError(await res.json()); } catch {}
      throw new Error(msg);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  function toFD(data) {
    if (data instanceof FormData) return data;
    const fd = new FormData();
    Object.entries(data).forEach(([k, v]) => v != null && fd.append(k, v));
    return fd;
  }

  return {
    get:     (path, opts)       => request(path, { method: 'GET', ...opts }),
    post:    (path, body, opts) => request(path, { method: 'POST', body, ...opts }),
    put:     (path, body, opts) => request(path, { method: 'PUT', body, ...opts }),
    delete:  (path, opts)       => request(path, { method: 'DELETE', ...opts }),
    postForm:(path, data)       => request(path, { method: 'POST', body: toFD(data) }),
    putForm: (path, data)       => request(path, { method: 'PUT',  body: toFD(data) }),

    async download(path) {
      const res = await fetch(`${API}${path}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(`Ошибка скачивания: HTTP ${res.status}`);
      return res;
    },

    /* ── Streaming NDJSON ──
     * Вызов: api.stream(path, formData, { onChunk, onDone, onError })
     * onChunk(stage, content) — вызывается при каждом progress-событии
     * onDone(message)         — вызывается с финальным объектом сообщения
     * onError(msg)            — вызывается при ошибке
     */
    async stream(path, formData, { onChunk, onDone, onError }) {
      let res;
      try {
        res = await fetch(`${API}${path}`, {
          method: 'POST',
          headers: authHeaders(),
          body: formData,
        });
      } catch {
        onError('Нет соединения с сервером. Проверьте подключение.');
        return;
      }

      if (!res.ok) {
        let msg = `Ошибка сервера (${res.status})`;
        try { msg = parseError(await res.json()); } catch {}
        onError(msg);
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = '';

      while (true) {
        let done, value;
        try {
          ({ done, value } = await reader.read());
        } catch {
          onError('Соединение прервано. Попробуйте ещё раз.');
          return;
        }
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // последняя неполная строка

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          let event;
          try { event = JSON.parse(trimmed); } catch { continue; }

          if (event.type === 'error') {
            onError('Агент не смог обработать запрос. Попробуйте переформулировать.');
            return;
          }
          if (event.type === 'progress') {
            onChunk(event.stage, event.content);
          }
          // Финальное событие — объект с ключом "message"
          if (event.message) {
            onDone(event.message);
          }
        }
      }

      // Обработать остаток буфера
      if (buffer.trim()) {
        try {
          const event = JSON.parse(buffer.trim());
          if (event.message) onDone(event.message);
          if (event.type === 'error') onError('Ошибка агента. Попробуйте ещё раз.');
        } catch {}
      }
    },
  };
})();
