function ProfileModal({ user, onClose, onLogout, onUserUpdated }) {
  const [tab, setTab]       = React.useState('info');
  const [form, setForm]     = React.useState({
    name: user?.name || '', surname: user?.surname || '',
    patronymic: user?.patronymic || '',
    username: user?.username || '', email: user?.email || '',
  });
  const [pwd, setPwd]       = React.useState({ old_password: '', new_password: '', confirm: '' });
  const [errors, setErrors] = React.useState({});
  const [loading, setLoading] = React.useState(false);

  function validateInfo() {
    const e = {};
    if (!form.name.trim())     e.name     = 'Введите имя';
    if (!form.surname.trim())  e.surname  = 'Введите фамилию';
    if (!form.username.trim()) e.username = 'Введите имя пользователя';
    if (!form.email.trim())    e.email    = 'Введите email';
    return e;
  }

  function validatePwd() {
    const e = {};
    if (!pwd.old_password) e.old_password = 'Введите текущий пароль';
    if (!pwd.new_password) e.new_password = 'Введите новый пароль';
    if (pwd.new_password && pwd.new_password !== pwd.confirm) e.confirm = 'Пароли не совпадают';
    return e;
  }

  async function saveInfo() {
    const e = validateInfo(); setErrors(e);
    if (Object.keys(e).length) return;
    setLoading(true);
    try {
      const updated = await api.putForm('/user/me/update-info/', {
        name: form.name, surname: form.surname,
        patronymic: form.patronymic || null,
        username: form.username, email: form.email,
      });
      Auth.saveUser({ ...user, ...updated });
      onUserUpdated({ ...user, ...updated });
      toast.success('Профиль успешно обновлён');
      onClose();
    } catch (err) {
      toast.error('Не удалось обновить профиль. Возможно, имя пользователя уже занято.');
    } finally { setLoading(false); }
  }

  async function savePassword() {
    const e = validatePwd(); setErrors(e);
    if (Object.keys(e).length) return;
    setLoading(true);
    try {
      await api.putForm('/user/me/change-password/', {
        old_password: pwd.old_password,
        new_password: pwd.new_password,
      });
      toast.success('Пароль успешно изменён');
      onClose();
    } catch {
      toast.error('Не удалось изменить пароль. Проверьте текущий пароль.');
    } finally { setLoading(false); }
  }

  async function deleteAccount() {
    if (!window.confirm('Удалить аккаунт? Все данные будут удалены безвозвратно.')) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('confirmation', 'true');
      await api.delete('/user/me/delete/', { body: fd });
      Auth.clear();
      onLogout();
    } catch {
      toast.error('Не удалось удалить аккаунт. Попробуйте позже.');
    } finally { setLoading(false); }
  }

  const fi = k => ({
    className: `input-field${errors[k] ? ' has-error' : ''}`,
    value: form[k],
    onChange: e => setForm(p => ({ ...p, [k]: e.target.value })),
  });
  const fp = k => ({
    className: `input-field${errors[k] ? ' has-error' : ''}`,
    value: pwd[k],
    onChange: e => setPwd(p => ({ ...p, [k]: e.target.value })),
    type: 'password',
  });

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-title">Редактировать профиль</div>

        <div className="modal-avatar">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.6">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round"/>
          </svg>
        </div>

        {tab === 'info' && (
          <>
            <div className="input-with-label">
              <label>Имя пользователя</label>
              <input {...fi('username')} placeholder="Username"/>
              {errors.username && <div className="field-error">{errors.username}</div>}
            </div>
            <div className="input-with-label">
              <label>Почта</label>
              <input {...fi('email')} placeholder="email@example.com" type="email"/>
              {errors.email && <div className="field-error">{errors.email}</div>}
            </div>
            <div className="input-with-label">
              <label>Имя</label>
              <input {...fi('name')} placeholder="Имя"/>
              {errors.name && <div className="field-error">{errors.name}</div>}
            </div>
            <div className="input-with-label">
              <label>Фамилия</label>
              <input {...fi('surname')} placeholder="Фамилия"/>
              {errors.surname && <div className="field-error">{errors.surname}</div>}
            </div>
            <div className="input-with-label">
              <label>Отчество (необязательно)</label>
              <input {...fi('patronymic')} placeholder="Отчество"/>
            </div>
            <a className="change-pwd-link" onClick={() => { setTab('password'); setErrors({}); }}>
              Изменить пароль
            </a>
            <div className="modal-btns">
              <button className="btn-cancel" onClick={onClose}>Отменить</button>
              <button className="btn-save" onClick={saveInfo} disabled={loading}>
                {loading ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
            <div style={{ textAlign:'center', marginTop:14, display:'flex', justifyContent:'center', gap:20 }}>
              <button onClick={onLogout}
                style={{ background:'none', border:'none', color:'#888', fontSize:13, cursor:'pointer' }}>
                Выйти из аккаунта
              </button>
              <button onClick={deleteAccount} disabled={loading}
                style={{ background:'none', border:'none', color:'#dc2626', fontSize:13, cursor:'pointer' }}>
                Удалить аккаунт
              </button>
            </div>
          </>
        )}

        {tab === 'password' && (
          <>
            <div className="input-with-label">
              <label>Текущий пароль</label>
              <input {...fp('old_password')} placeholder="Текущий пароль"/>
              {errors.old_password && <div className="field-error">{errors.old_password}</div>}
            </div>
            <div className="input-with-label">
              <label>Новый пароль</label>
              <input {...fp('new_password')} placeholder="Мин. 8 символов, A-Z, 0-9, спецсимвол"/>
              {errors.new_password && <div className="field-error">{errors.new_password}</div>}
            </div>
            <div className="input-with-label">
              <label>Повторите новый пароль</label>
              <input {...fp('confirm')} placeholder="Повторите пароль"/>
              {errors.confirm && <div className="field-error">{errors.confirm}</div>}
            </div>
            <div className="modal-btns">
              <button className="btn-cancel" onClick={() => { setTab('info'); setErrors({}); }}>Назад</button>
              <button className="btn-save" onClick={savePassword} disabled={loading}>
                {loading ? 'Сохранение...' : 'Изменить пароль'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
