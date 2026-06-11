function RegisterPage({ setPage, onLogin }) {
  const [form, setForm] = React.useState({
    name: '', surname: '', patronymic: '',
    username: '', email: '', password: '', confirm: '',
    user_agreement_accepted: false,
    personal_data_processing_accepted: false,
  });
  const [errors, setErrors] = React.useState({});
  const [loading, setLoading] = React.useState(false);

  function validate() {
    const e = {};
    if (!form.name.trim())     e.name     = 'Введите имя';
    if (!form.surname.trim())  e.surname  = 'Введите фамилию';
    if (!form.username.trim()) e.username = 'Введите имя пользователя';
    if (!form.email.trim())    e.email    = 'Введите email';
    if (!form.password)        e.password = 'Введите пароль';
    if (form.password && form.password !== form.confirm) e.confirm = 'Пароли не совпадают';
    if (!form.user_agreement_accepted)           e.terms  = 'Примите пользовательское соглашение';
    if (!form.personal_data_processing_accepted) e.policy = 'Примите политику обработки данных';
    return e;
  }

  async function handleRegister() {
    const e = validate(); setErrors(e);
    if (Object.keys(e).length) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('name',     form.name);
      fd.append('surname',  form.surname);
      if (form.patronymic) fd.append('patronymic', form.patronymic);
      fd.append('username', form.username);
      fd.append('email',    form.email);
      fd.append('password', form.password);
      fd.append('user_agreement_accepted',           'true');
      fd.append('personal_data_processing_accepted', 'true');
      await api.postForm('/user/register/', fd);

      // Автологин после регистрации
      const lfd = new FormData();
      lfd.append('username', form.username);
      lfd.append('password', form.password);
      const tokens = await api.postForm('/user/login/', lfd);
      Auth.save(tokens.access_token, tokens.refresh_token);
      const me = await api.get('/user/me/');
      Auth.saveUser(me);
      toast.success('Добро пожаловать!');
      onLogin(me);
    } catch {
      toast.error('Не удалось зарегистрироваться. Возможно, такой пользователь уже существует.');
    } finally { setLoading(false); }
  }

  const canSubmit = form.user_agreement_accepted && form.personal_data_processing_accepted
    && form.name && form.surname && form.username && form.email && form.password;

  const f = k => ({
    className: `input-field${errors[k] ? ' has-error' : ''}`,
    value: form[k],
    onChange: e => setForm(p => ({ ...p, [k]: e.target.value })),
  });

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

        <input {...f('name')}      placeholder="Имя"/>
        {errors.name    && <div className="field-error">{errors.name}</div>}
        <input {...f('surname')}   placeholder="Фамилия"/>
        {errors.surname && <div className="field-error">{errors.surname}</div>}
        <input {...f('patronymic')} placeholder="Отчество (необязательно)"/>
        <input {...f('username')}  placeholder="Username"/>
        {errors.username && <div className="field-error">{errors.username}</div>}
        <input {...f('email')} placeholder="E-mail" type="email"/>
        {errors.email && <div className="field-error">{errors.email}</div>}
        <input
          className={`input-field${errors.password ? ' has-error' : ''}`}
          placeholder="Пароль (A-Z, 0-9, спецсимвол, мин. 8)"
          type="password" value={form.password}
          onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
          autoComplete="new-password"
        />
        {errors.password && <div className="field-error">{errors.password}</div>}
        <input
          className={`input-field${errors.confirm ? ' has-error' : ''}`}
          placeholder="Повторите пароль"
          type="password" value={form.confirm}
          onChange={e => setForm(p => ({ ...p, confirm: e.target.value }))}
          autoComplete="new-password"
        />
        {errors.confirm && <div className="field-error">{errors.confirm}</div>}

        <div style={{ height: 8 }}/>

        <label className="checkbox-row">
          <input type="checkbox" checked={form.user_agreement_accepted}
            onChange={e => setForm(p => ({ ...p, user_agreement_accepted: e.target.checked }))}/>
          <span>Я принимаю <a href="agreement.html" target="_blank">Пользовательское соглашение</a></span>
        </label>
        {errors.terms && <div className="field-error">{errors.terms}</div>}

        <label className="checkbox-row">
          <input type="checkbox" checked={form.personal_data_processing_accepted}
            onChange={e => setForm(p => ({ ...p, personal_data_processing_accepted: e.target.checked }))}/>
          <span>Я согласен с <a href="privacy.html" target="_blank">Политикой обработки персональных данных</a></span>        </label>
        {errors.policy && <div className="field-error">{errors.policy}</div>}

        <button className="btn-primary" disabled={!canSubmit || loading} onClick={handleRegister}>
          {loading ? 'Регистрация...' : 'Зарегистрироваться'}
        </button>

        <div className="auth-link">
          Уже есть аккаунт? <span onClick={() => setPage('login')}>Войдите.</span>
        </div>
      </div>
    </div>
  );
}
