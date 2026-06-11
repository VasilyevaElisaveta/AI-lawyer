function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="1 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}
function DocIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  );
}
function BotAvatar() {
  return (
    <div className="bot-avatar">
      <svg width="18" height="18" viewBox="0 0 32 32" fill="#277F4B">
        <rect x="6" y="10" width="20" height="14" rx="4"/>
        <rect x="10" y="15" width="4" height="4" rx="2" fill="white"/>
        <rect x="18" y="15" width="4" height="4" rx="2" fill="white"/>
        <rect x="14" y="6" width="4" height="5" rx="2"/>
        <rect x="3" y="16" width="3" height="6" rx="1.5"/>
        <rect x="26" y="16" width="3" height="6" rx="1.5"/>
      </svg>
    </div>
  );
}

function Stars({ messageId, currentRating, chatId }) {
  const [rating, setRating] = React.useState(currentRating || 0);
  const [hover,  setHover]  = React.useState(0);
  const [sent,   setSent]   = React.useState(!!currentRating);

  async function handleRate(val) {
    if (sent) return;
    try {
      await api.post(`/chat/${chatId}/message/${messageId}/rate/`, { rating: val });
      setRating(val); setSent(true);
      toast.success('Спасибо за оценку!');
    } catch { toast.error('Не удалось сохранить оценку'); }
  }

  return (
    <div className="msg-rating">
      {[1,2,3,4,5].map(n => (
        <button key={n}
          className={`star-btn ${n <= (hover || rating) ? 'star-btn--filled' : ''}`}
          onMouseEnter={() => !sent && setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => handleRate(n)}
          style={{ cursor: sent ? 'default' : 'pointer' }}
          title={sent ? `Оценка: ${rating}` : `Оценить на ${n}`}
        >★</button>
      ))}
    </div>
  );
}

function renderText(text) {
  if (!text) return null;
  return text.split(/(\*\*[^*]+\*\*)/g).map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <b key={i}>{p.slice(2,-2)}</b>;
    return p.split('\n').map((line, j, arr) => (
      <React.Fragment key={`${i}-${j}`}>
        {line}{j < arr.length - 1 ? <br/> : null}
      </React.Fragment>
    ));
  });
}

const AGENT_HINTS = {
  auto:             null,
  general_question: 'Режим: консультация',
  pretrial_claim:   'Режим: претензия',
  lawsuit:          'Режим: исковое заявление',
  contract:         'Режим: договор',
};

// Потоковый курсор
function Cursor() {
  return <span style={{
    display: 'inline-block', width: 2, height: '1em',
    background: '#277F4B', marginLeft: 2, verticalAlign: 'text-bottom',
    animation: 'blink .7s step-end infinite',
  }}/>;
}

function ChatPage({ user, sidebarOpen, setSidebar }) {
  const [chats,       setChats]       = React.useState([]);
  const [activeChatId, setActive]     = React.useState(null);
  const [messages,    setMessages]    = React.useState([]);
  const [input,       setInput]       = React.useState('');
  const [streaming,   setStreaming]   = React.useState(false); // идёт стриминг
  const [loadingChat, setLoadingChat] = React.useState(false);
  const [agentType,   setAgentType]   = React.useState('auto');

  const activeRef    = React.useRef(null);
  const endRef       = React.useRef(null);
  const textRef      = React.useRef(null);
  const streamingRef = React.useRef(false); // синхронный флаг

  React.useEffect(() => { activeRef.current = activeChatId; }, [activeChatId]);

  React.useEffect(() => {
    api.get('/chat/history/')
      .then(d => setChats(d.chats || []))
      .catch(() => toast.error('Не удалось загрузить историю чатов'));
  }, []);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  React.useEffect(() => {
    if (textRef.current) {
      textRef.current.style.height = 'auto';
      textRef.current.style.height = Math.min(textRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  function handleNewChat() {
    if (streamingRef.current) return;
    setActive(null); activeRef.current = null;
    setMessages([]); setInput('');
  }

  async function handleSelectChat(chat) {
    if (activeRef.current === chat.id || streamingRef.current) return;
    setActive(chat.id); activeRef.current = chat.id;
    setMessages([]); setLoadingChat(true);
    try {
      const data = await api.get(`/chat/${chat.id}/`);
      if (activeRef.current === chat.id) setMessages(data.messages || []);
    } catch { toast.error('Не удалось загрузить сообщения'); }
    finally { setLoadingChat(false); }
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || streamingRef.current) return;

    // Создать чат если нет активного
    let cid = activeRef.current;
    if (!cid) {
      try {
        const c = await api.post('/chat/create/', null);
        cid = c.id;
        setActive(cid); activeRef.current = cid;
        setChats(prev => [c, ...prev]);
      } catch { toast.error('Не удалось создать чат'); return; }
    }

    setInput('');
    if (textRef.current) textRef.current.style.height = 'auto';

    // Добавить сообщение пользователя
    const userMsg = { id: `h-${Date.now()}`, role: 'human', text, files: [] };
    setMessages(prev => [...prev, userMsg]);

    // Добавить пустое сообщение агента — будем наполнять стримом
    const streamId = `stream-${Date.now()}`;
    setMessages(prev => [...prev, { id: streamId, role: 'ai', text: '', files: [], _streaming: true }]);

    setStreaming(true);
    streamingRef.current = true;

    // Формируем сообщение с префиксом агента если выбран конкретный
    const msgText = agentType !== 'auto' ? `[agent:${agentType}] ${text}` : text;
    const fd = new FormData();
    fd.append('message', msgText);

    await api.stream(`/chat/${cid}/message/stream/`, fd, {
      onChunk(stage, content) {
        // Дописываем текст в потоковое сообщение
        if (stage === 'answer' || stage === 'document_comment') {
          setMessages(prev => prev.map(m =>
            m.id === streamId
              ? { ...m, text: m.text + content }
              : m
          ));
        }
      },
      onDone(finalMsg) {
        // Заменяем временное сообщение финальным (с id, files, rating из БД)
        setMessages(prev => prev.map(m =>
          m.id === streamId
            ? { ...finalMsg, _streaming: false }
            : m
        ));
        // Обновить название чата в сайдбаре
        setChats(prev => prev.map(c =>
          c.id === cid ? { ...c, name: c.name || text.slice(0, 50) } : c
        ));
        setStreaming(false);
        streamingRef.current = false;
      },
      onError(msg) {
        // Убрать пустое потоковое сообщение, показать ошибку
        setMessages(prev => prev.filter(m => m.id !== streamId));
        toast.error(msg);
        setStreaming(false);
        streamingRef.current = false;
      },
    });
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  async function downloadFile(fileId, fileName) {
    try {
      const res  = await api.download(`/documents/${fileId}/`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = fileName;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
      toast.success('Документ скачан');
    } catch { toast.error('Не удалось скачать документ'); }
  }

  const showWelcome = !activeChatId && messages.length === 0 && !loadingChat;

  return (
    <div className={`app-layout ${sidebarOpen ? 'app-layout--sidebar-open' : ''}`}>
      <button className="sidebar-toggle"
        onClick={() => setSidebar(v => !v)}
        style={{ left: sidebarOpen ? 'var(--sidebar-w)' : 0 }}
        title={sidebarOpen ? 'Скрыть историю' : 'Показать историю'}>
        {sidebarOpen ? '‹' : '›'}
      </button>

      {sidebarOpen && (
        <Sidebar
          chats={chats}
          setChats={setChats}
          activeChatId={activeChatId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
        />
      )}

      <main className="chat-main">
        {/* Шапка с выбором агента */}
        <div className="chat-topbar">
          <div className="chat-topbar__left">
            {/*<AgentSelector selected={agentType} onChange={setAgentType} disabled={streaming}/>
            {AGENT_HINTS[agentType] && (
              <span className="chat-agent-hint">{AGENT_HINTS[agentType]}</span>
            )}*/}
          </div>
          {activeChatId && !streaming && (
            <button className="chat-topbar__new" onClick={handleNewChat}>+ Новый чат</button>
          )}
          {streaming && (
            <span style={{ fontSize: 12, color: '#888', fontStyle: 'italic' }}>Агент печатает...</span>
          )}
        </div>

        {/* Сообщения */}
        <div className="messages-area">
          {showWelcome && (
            <div className="welcome-msg">
              Привет! Я ИИ-Юрист.<br/>
              Расскажи мне про свою ситуацию<br/>
              и я постараюсь тебе помочь.
            </div>
          )}

          {loadingChat && <div className="spinner"/>}

          {!loadingChat && messages.map((msg, i) => {
            const isUser = msg.role === 'human';
            return (
              <div key={msg.id || i} className={`msg-row ${isUser ? 'msg-row--user' : 'msg-row--bot'}`}>
                {!isUser && <BotAvatar/>}
                <div className="msg-col">
                  <div className={`bubble ${isUser ? 'bubble--user' : 'bubble--bot'}`}>
                    {renderText(msg.text)}
                    {/* Мигающий курсор во время стриминга */}
                    {msg._streaming && <Cursor/>}
                    {/* Прикреплённые файлы */}
                    {msg.files && msg.files.length > 0 && (
                      <div className="file-list">
                        {msg.files.map(f => (
                          <button key={f.id} className="file-link"
                            onClick={() => downloadFile(f.id, f.name)}>
                            <DocIcon/> {f.name} ⬇
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {/* Звёздочки только для сохранённых сообщений агента */}
                  {!isUser && activeChatId && !msg._streaming && typeof msg.id === 'number' && (
                    <Stars messageId={msg.id} currentRating={msg.rating} chatId={activeChatId}/>
                  )}
                </div>
              </div>
            );
          })}

          <div ref={endRef}/>
        </div>

        {/* Поле ввода */}
        <div className="input-area">
          <div className="input-row">
            <textarea ref={textRef} className="chat-input"
              placeholder={streaming ? 'Подождите ответа агента...' : 'Напишите ваш вопрос...'}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
              disabled={streaming}
            />
            <button className="send-btn" onClick={sendMessage}
              disabled={!input.trim() || streaming}
              title="Отправить (Enter)">
              <SendIcon/>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
