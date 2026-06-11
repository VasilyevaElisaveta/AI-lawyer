/* Компонент выбора агента в шапке чата */
//
const AGENTS = [
  {
    id: 'auto',
    label: 'Авто',
    description: 'Маршрутизатор сам выберет агента',
    icon: '🤖',
  },
  {
    id: 'claims_agent',
    label: 'Иски и претензии',
    description: 'Напрямую к агенту по документам',
    icon: '⚖️',
  },
  {
    id: 'general_questions_agent',
    label: 'Общие вопросы',
    description: 'Напрямую к агенту консультаций',
    icon: '💬',
  },
  {
    id: 'router_agent',
    label: 'Маршрутизатор',
    description: 'Только классификация без ответа',
    icon: '🔀',
  },
];
function AgentSelector({ selected, onChange }) {
  const [open, setOpen] = React.useState(false);
  const ref             = React.useRef(null);

  // Закрыть при клике снаружи
  React.useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const current = AGENTS.find(a => a.id === selected) || AGENTS[0];

  return (
    <div className="agent-selector" ref={ref}>
      <button
        className="agent-selector__trigger"
        onClick={() => setOpen(v => !v)}
        title="Выбрать тип агента"
      >
        <span className="agent-selector__icon">{current.icon}</span>
        <span className="agent-selector__label">{current.label}</span>
        <svg
          width="12" height="12" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="2.5"
          style={{ transition: 'transform .2s', transform: open ? 'rotate(180deg)' : 'none' }}
        >
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {open && (
        <div className="agent-selector__dropdown">
          <div className="agent-selector__dropdown-title">Выберите тип помощи</div>
          {AGENTS.map(agent => (
            <button
              key={agent.id}
              className={`agent-selector__option ${selected === agent.id ? 'agent-selector__option--active' : ''}`}
              onClick={() => { onChange(agent.id); setOpen(false); }}
            >
              <span className="agent-option__icon">{agent.icon}</span>
              <div className="agent-option__text">
                <div className="agent-option__label">{agent.label}</div>
                <div className="agent-option__desc">{agent.description}</div>
              </div>
              {selected === agent.id && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke="#277F4B" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
