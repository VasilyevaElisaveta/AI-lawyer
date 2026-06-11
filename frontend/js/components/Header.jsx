function RobotIcon({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect x="6" y="10" width="20" height="14" rx="4" fill="currentColor"/>
      <rect x="10" y="15" width="4" height="4" rx="2" fill="white"/>
      <rect x="18" y="15" width="4" height="4" rx="2" fill="white"/>
      <rect x="14" y="6" width="4" height="5" rx="2" fill="currentColor"/>
      <rect x="3" y="16" width="3" height="6" rx="1.5" fill="currentColor"/>
      <rect x="26" y="16" width="3" height="6" rx="1.5" fill="currentColor"/>
    </svg>
  );
}

function UserIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="8" r="4"/>
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round"/>
    </svg>
  );
}

function Header({ page, setPage, user, onProfileOpen }) {
  const isChat  = page === 'chat';
  const isDocs  = page === 'documents';
  const isAdmin = page === 'admin';

  return (
    <header className="header">
      <div className="header-logo" onClick={() => user && setPage(user.is_admin ? 'admin' : 'chat')}>
        <RobotIcon size={28}/>
        <span>{user && user.is_admin && isAdmin ? 'Панель управления' : 'ИИ-Юрист'}</span>
      </div>

      {user && (
        <nav className="header-nav">
              <button className={`btn-nav ${isChat ? 'btn-nav--active' : 'btn-nav--inactive'}`}
                onClick={() => setPage('admin')}>Статистика</button>
              <button className={`btn-nav ${isChat ? 'btn-nav--active' : 'btn-nav--inactive'}`}
                onClick={() => setPage('chat')}>Агент</button>
              <button className={`btn-nav ${isDocs ? 'btn-nav--active' : 'btn-nav--inactive'}`}
                onClick={() => setPage('documents')}>Документы</button>

          <button className="avatar-btn" onClick={onProfileOpen} title="Профиль">
            <UserIcon size={18}/>
          </button>
          <span className="header-username">{user.username}</span>
        </nav>
      )}
    </header>
  );
}
