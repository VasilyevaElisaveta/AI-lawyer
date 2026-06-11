function LoginPage({ setPage, onLogin }) {
  const [form, setForm]     = React.useState({ username: '', password: '' });
  const [errors, setErrors] = React.useState({});
  const [loading, setLoading] = React.useState(false);

  function validate() {
    const e = {};
    if (!form.username.trim()) e.username = 'Введите имя пользователя';
    if (!form.password)        e.password = 'Введите пароль';
    return e;
  }

  async function handleLogin() {
    const e = validate(); setErrors(e);
    if (Object.keys(e).length) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('username', form.username);
      fd.append('password', form.password);
      const data = await api.postForm('/user/login/', fd);
      Auth.save(data.access_token, data.refresh_token);
      const me = await api.get('/user/me/');
      Auth.saveUser(me);
      onLogin(me);
    } catch {
      toast.error('Неверное имя пользователя или пароль');
      setErrors({ password: ' ' });
    } finally { setLoading(false); }
  }

  const handleKey = e => { if (e.key === 'Enter') handleLogin(); };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-title">
          Привет! Я ИИ-Юрист.<br/>
          Создайте аккаунт или войдите в существующий,<br/>
          чтобы получить юридическую помощь бесплатно.
        </div>
        <div className="avatar-placeholder">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round"/>
          </svg>
        </div>

        <input
          className={`input-field${errors.username ? ' has-error' : ''}`}
          placeholder="E-mail или Username"
          value={form.username}
          onChange={e => setForm(p => ({ ...p, username: e.target.value }))}
          onKeyDown={handleKey}
          autoComplete="username"
        />
        {errors.username && <div className="field-error">{errors.username}</div>}

        <input
          className={`input-field${errors.password ? ' has-error' : ''}`}
          placeholder="Пароль"
          type="password"
          value={form.password}
          onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
          onKeyDown={handleKey}
          autoComplete="current-password"
        />
        {errors.password && errors.password !== ' ' && (
          <div className="field-error">{errors.password}</div>
        )}

        <button
          className="btn-primary"
          disabled={loading || !form.username || !form.password}
          onClick={handleLogin}
        >
          {loading ? 'Входим...' : 'Войти'}
        </button>

        <div className="auth-link">
          Нет аккаунта?{' '}
          <span onClick={() => setPage('register')}>Зарегистрируйтесь.</span>
        </div>
      </div>
    </div>
  );
}
