function App() {
  const [user, setUser]         = React.useState(() => Auth.getUser());
  const [page, setPage]         = React.useState(() => {
    if (!Auth.isLoggedIn()) return 'login';
    return localStorage.getItem('last_page') || 'chat';
  });
  const [showProfile, setShowProfile] = React.useState(false);
  const [sidebarOpen, setSidebar]     = React.useState(true);

  React.useEffect(() => {
    if (!Auth.isLoggedIn()) return;
    api.get('/user/me/')
      .then(me => { Auth.saveUser(me); setUser(me); })
      .catch(() => { Auth.clear(); setUser(null); navigateTo('login'); });
  }, []);

  function navigateTo(p) {
    localStorage.setItem('last_page', p);
    setPage(p);
  }

  function handleLogin(me) {
    setUser(me);
    navigateTo('chat');
  }

  function handleLogout() {
    Auth.clear();
    setUser(null);
    navigateTo('login');
    setShowProfile(false);
  }

  function handleUserUpdated(updated) {
    setUser(updated);
    Auth.saveUser(updated);
  }

  return (
    <>
      <Toast/>
      <Header
        page={page}
        setPage={navigateTo}
        user={user}
        onProfileOpen={() => setShowProfile(true)}
      />

      {/* Страницы без авторизации */}
      {!user && page === 'login'    && <LoginPage    setPage={navigateTo} onLogin={handleLogin}/>}
      {!user && page === 'register' && <RegisterPage setPage={navigateTo} onLogin={handleLogin}/>}

      {/* Страницы с авторизацией */}
      {user && page === 'chat' && (
        <ChatPage
          user={user}
          sidebarOpen={sidebarOpen}
          setSidebar={setSidebar}
        />
      )}

      {user && page === 'documents' && (
        <DocumentsPage
          user={user}
          sidebarOpen={sidebarOpen}
          setSidebar={setSidebar}
          onNavigateToChat={() => navigateTo('chat')}
        />
      )}

      {user && user.is_admin && page === 'admin' && <AdminPage user={user}/>}

      {/* Модалка профиля */}
      {showProfile && user && (
        <ProfileModal
          user={user}
          onClose={() => setShowProfile(false)}
          onLogout={handleLogout}
          onUserUpdated={handleUserUpdated}
        />
      )}
    </>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App/>);
