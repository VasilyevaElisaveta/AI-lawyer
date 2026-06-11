function HistoryIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9"/>
      <polyline points="12 7 12 12 15 15"/>
    </svg>
  );
}

function ChatItem({
  chat, isActive, isRenaming, inputRef,
  onSelect, onStartRename, onCommitRename, onCancelRename, onDelete,
}) {
  const [hovered, setHovered] = React.useState(false);
  const label = chat.name
    ? (chat.name.length > 28 ? chat.name.slice(0, 28) + '...' : chat.name)
    : 'Новый чат';

  if (isRenaming) {
    return (
      <div className={`chat-item ${isActive ? 'chat-item--active' : ''}`}
        style={{ padding: '5px 10px' }}>
        <input
          ref={inputRef}
          defaultValue={chat.name || ''}
          onBlur={e => onCommitRename(chat, e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter')  onCommitRename(chat, e.target.value);
            if (e.key === 'Escape') onCancelRename();
          }}
          style={{
            width: '100%', border: '1.5px solid #277F4B',
            borderRadius: 6, padding: '4px 8px',
            fontSize: 13, fontFamily: 'inherit', outline: 'none',
          }}
        />
      </div>
    );
  }

  return (
    <div
      className={`chat-item ${isActive ? 'chat-item--active' : ''}`}
      style={{ display: 'flex', alignItems: 'center', gap: 4 }}
      onClick={() => onSelect(chat)}
      onDoubleClick={e => onStartRename(chat, e)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title="Двойной клик — переименовать"
    >
      <span style={{ flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
        {label}
      </span>
      {hovered && (
        <button
          onClick={e => onDelete(chat, e)}
          title="Удалить чат"
          style={{
            background:'none', border:'none', cursor:'pointer',
            color:'#aaa', fontSize:16, lineHeight:1,
            padding:'0 2px', flexShrink:0,
            display:'flex', alignItems:'center',
          }}
          onMouseEnter={e => e.currentTarget.style.color = '#dc2626'}
          onMouseLeave={e => e.currentTarget.style.color = '#aaa'}
        >×</button>
      )}
    </div>
  );
}

function Sidebar({ chats, setChats, activeChatId, onNewChat, onSelectChat }) {
  const [renamingId, setRenamingId] = React.useState(null);
  const inputRef = React.useRef(null);

  const now            = new Date();
  const startToday     = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startYesterday = new Date(startToday); startYesterday.setDate(startYesterday.getDate() - 1);
  const startWeek      = new Date(startToday); startWeek.setDate(startWeek.getDate() - 7);

  const groups = { today: [], yesterday: [], week: [], older: [] };
  (chats || []).forEach(c => {
    const d = new Date(c.created_at);
    if (d >= startToday)          groups.today.push(c);
    else if (d >= startYesterday) groups.yesterday.push(c);
    else if (d >= startWeek)      groups.week.push(c);
    else                          groups.older.push(c);
  });

  function startRename(chat, e) {
    e.stopPropagation();
    setRenamingId(chat.id);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function commitRename(chat, value) {
    const name = (value || '').trim();
    setRenamingId(null);
    if (!name || name === chat.name) return;
    try {
      await api.putForm(`/chat/${chat.id}/rename/`, { new_name: name });
      setChats(prev => prev.map(c => c.id === chat.id ? { ...c, name } : c));
      toast.success('Чат переименован');
    } catch {
      toast.error('Не удалось переименовать чат');
    }
  }

  function cancelRename() { setRenamingId(null); }

  async function deleteChat(chat, e) {
    e.stopPropagation();
    if (!window.confirm(`Удалить чат «${chat.name || 'Новый чат'}»?`)) return;
    try {
      await api.delete(`/chat/${chat.id}/`);
      setChats(prev => prev.filter(c => c.id !== chat.id));
      toast.success('Чат удалён');
    } catch {
      toast.error('Не удалось удалить чат');
    }
  }

  function Group({ title, items }) {
    if (!items.length) return null;
    return (
      <>
        <div className="sidebar-group-label">{title}</div>
        {items.map(c => (
          <ChatItem
            key={c.id}
            chat={c}
            isActive={activeChatId === c.id}
            isRenaming={renamingId === c.id}
            inputRef={inputRef}
            onSelect={onSelectChat}
            onStartRename={startRename}
            onCommitRename={commitRename}
            onCancelRename={cancelRename}
            onDelete={deleteChat}
          />
        ))}
      </>
    );
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <HistoryIcon/> История чатов
      </div>
      <button className="new-chat-btn" onClick={onNewChat}>+ Новый чат</button>
      <div className="sidebar-chats">
        <Group title="Сегодня"           items={groups.today}/>
        <Group title="Вчера"             items={groups.yesterday}/>
        <Group title="На прошлой неделе" items={groups.week}/>
        <Group title="Раньше"            items={groups.older}/>
        {!chats.length && (
          <div style={{ padding:'20px 16px', fontSize:12, color:'#bbb', textAlign:'center' }}>
            Нет чатов
          </div>
        )}
      </div>
      <div className="sidebar-bottom">Поддержка</div>
    </aside>
  );
}
