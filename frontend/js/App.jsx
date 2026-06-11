function App() {
  const [user, setUser]         = React.useState(() => Auth.getUser());
  const [page, setPage]         = React.useState(() => {
    if (!Auth.isLoggedIn()) return 'login';
    const u = Auth.getUser();
    return u && u.is_admin ? 'admin' : 'chat';
  });
  const [showProfile, setShowProfile] = React.useState(false);
  const [sidebarOpen, setSidebar]     = React.useState(true);

  React.useEffect(() => {
    if (!Auth.isLoggedIn()) return;
    api.get('/user/me/')
      .then(me => { Auth.saveUser(me); setUser(me); })
      .catch(() => { Auth.clear(); setUser(null); setPage('login'); });
  }, []);

  function handleLogin(me) {
    setUser(me);
    setPage(me.is_admin ? 'admin' : 'chat');
  }

  function handleLogout() {
    Auth.clear();
    setUser(null);
    setPage('login');
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
        setPage={setPage}
        user={user}
        onProfileOpen={() => setShowProfile(true)}
      />

      {/* Страницы без авторизации */}
      {!user && page === 'login'    && <LoginPage    setPage={setPage} onLogin={handleLogin}/>}
      {!user && page === 'register' && <RegisterPage setPage={setPage} onLogin={handleLogin}/>}

      {/* Страницы с авторизацией */}
      {user && page === 'chat'      && (
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
        />
      )}
      {user && page === 'admin' && <AdminPage user={user}/>}

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
