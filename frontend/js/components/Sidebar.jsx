function HistoryIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9"/>
      <polyline points="12 7 12 12 15 15"/>
    </svg>
  );
}

function Sidebar({ chats, setChats, activeChatId, onNewChat, onSelectChat }) {
  const [renamingId, setRenamingId] = React.useState(null);
  const [renameVal,  setRenameVal]  = React.useState('');
  const inputRef = React.useRef(null);

  const now        = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startWeek  = new Date(startToday); startWeek.setDate(startWeek.getDate() - 7);

  const groups = { today: [], week: [], older: [] };
  (chats || []).forEach(c => {
    const d = new Date(c.created_at);
    if (d >= startToday)     groups.today.push(c);
    else if (d >= startWeek) groups.week.push(c);
    else                     groups.older.push(c);
  });

  function startRename(chat, e) {
    e.stopPropagation();
    setRenamingId(chat.id);
    setRenameVal(chat.name || '');
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function commitRename(chat) {
    const name = renameVal.trim();
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

  function handleRenameKey(e, chat) {
    if (e.key === 'Enter')  commitRename(chat);
    if (e.key === 'Escape') setRenamingId(null);
  }

  function ChatItem({ chat }) {
    const isActive  = activeChatId === chat.id;
    const isRenaming = renamingId === chat.id;
    const label = chat.name
      ? (chat.name.length > 30 ? chat.name.slice(0, 30) + '...' : chat.name)
      : 'Новый чат';

    if (isRenaming) {
      return (
        <div className={`chat-item ${isActive ? 'chat-item--active' : ''}`}
          style={{ padding: '5px 10px' }}>
          <input
            ref={inputRef}
            value={renameVal}
            onChange={e => setRenameVal(e.target.value)}
            onBlur={() => commitRename(chat)}
            onKeyDown={e => handleRenameKey(e, chat)}
            style={{
              width: '100%', border: '1.5px solid #277F4B', borderRadius: 6,
              padding: '4px 8px', fontSize: 13, fontFamily: 'inherit', outline: 'none',
            }}
          />
        </div>
      );
    }

    return (
      <div
        className={`chat-item ${isActive ? 'chat-item--active' : ''}`}
        onClick={() => onSelectChat(chat)}
        onDoubleClick={e => startRename(chat, e)}
        title={`${chat.name || 'Новый чат'}\nДважды кликните для переименования`}
      >
        {label}
      </div>
    );
  }

  function Group({ title, items }) {
    if (!items.length) return null;
    return (
      <>
        <div className="sidebar-group-label">{title}</div>
        {items.map(c => <ChatItem key={c.id} chat={c}/>)}
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
        <Group title="На прошлой неделе" items={groups.week}/>
        <Group title="Раньше"            items={groups.older}/>
        {!chats.length && (
          <div style={{ padding: '20px 16px', fontSize: 12, color: '#bbb', textAlign: 'center' }}>
            Нет чатов
          </div>
        )}
      </div>

      <div className="sidebar-bottom">Поддержка</div>
    </aside>
  );
}
