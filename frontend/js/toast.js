const ToastBus = (() => {
  let _listener = null;
  return {
    subscribe(fn) { _listener = fn; },
    emit(t)       { _listener && _listener(t); },
  };
})();

function Toast() {
  const [toasts, setToasts] = React.useState([]);

  React.useEffect(() => {
    ToastBus.subscribe(t => {
      const id = Date.now() + Math.random();
      setToasts(prev => [...prev, { ...t, id }]);
      // Дольше показываем — 6 секунд
      setTimeout(() => setToasts(prev => prev.filter(x => x.id !== id)), t.duration || 6000);
    });
  }, []);

  const remove = id => setToasts(prev => prev.filter(x => x.id !== id));

  const icons = { error: '✕', success: '✓', info: 'ℹ' };

  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast--${t.type || 'info'}`}>
          <span className="toast-icon">{icons[t.type] || icons.info}</span>
          <span className="toast-msg">{t.message}</span>
          <button className="toast-close" onClick={() => remove(t.id)}>×</button>
        </div>
      ))}
    </div>
  );
}

const toast = {
  error:   msg => ToastBus.emit({ type: 'error',   message: msg }),
  success: msg => ToastBus.emit({ type: 'success', message: msg }),
  info:    msg => ToastBus.emit({ type: 'info',     message: msg }),
};
