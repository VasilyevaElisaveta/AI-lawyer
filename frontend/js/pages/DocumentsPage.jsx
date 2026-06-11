function DocumentsPage({ user, sidebarOpen, setSidebar, onNavigateToChat }) {
  const [docs, setDocs]       = React.useState([]);
  const [chats, setChats]     = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    Promise.all([
      api.get('/documents/'),
      api.get('/chat/history/'),
    ])
      .then(([d, h]) => { setDocs(d.documents || []); setChats(h.chats || []); })
      .catch(() => toast.error('Не удалось загрузить документы'))
      .finally(() => setLoading(false));
  }, []);

  async function downloadDoc(id, name) {
    try {
      const res  = await api.download(`/documents/${id}/`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = name;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Документ скачан');
    } catch {
      toast.error('Не удалось скачать документ. Попробуйте позже.');
    }
  }

  async function deleteDoc(id) {
    if (!window.confirm('Удалить документ?')) return;
    try {
      await api.delete(`/documents/${id}/`);
      setDocs(prev => prev.filter(d => d.id !== id));
      toast.success('Документ удалён');
    } catch {
      toast.error('Не удалось удалить документ');
    }
  }

  function formatDate(dt) {
    if (!dt) return '';
    return new Date(dt).toLocaleDateString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    });
  }

  return (
    <div className={`app-layout ${sidebarOpen ? 'app-layout--sidebar-open' : ''}`}>
      <button
        className="sidebar-toggle"
        onClick={() => setSidebar(v => !v)}
        style={{ left: sidebarOpen ? 'var(--sidebar-w)' : 0 }}
        title={sidebarOpen ? 'Скрыть историю' : 'Показать историю'}
      >
        {sidebarOpen ? '‹' : '›'}
      </button>

      {sidebarOpen && (
        <Sidebar
          chats={chats}
          activeChatId={null}
          onNewChat={() => {}}
          onSelectChat={(chat) => onNavigateToChat(chat.id)}
        />
      )}

      <div className="page-content">
        <div className="page-title">Документы</div>

        {loading && <div className="spinner"/>}

        {!loading && docs.length === 0 && (
          <div className="docs-empty">
            Документов пока нет.<br/>
            Они появятся здесь после того как агент создаст их в ходе диалога.
          </div>
        )}

        {!loading && docs.length > 0 && (
          <div className="docs-grid">
            {docs.map(doc => (
              <div key={doc.id} className="doc-card">
                <div className="doc-card-header">
                  <div className="doc-icon">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="1.8">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                  </div>
                  <div>
                    <div className="doc-name">{doc.file_name}</div>
                    {doc.chat_name && (
                      <div className="doc-chat">Чат: {doc.chat_name}</div>
                    )}
                    <div className="doc-chat">{formatDate(doc.created_at)}</div>
                  </div>
                </div>
                <div className="doc-actions">
                  <button className="doc-download" onClick={() => downloadDoc(doc.id, doc.file_name)}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2.2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Скачать DOCX
                  </button>
                  <button className="doc-delete" onClick={() => deleteDoc(doc.id)}>
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
