/* Выпадающий мультиселект с галочками */
function MultiSelect({ options, selected, onChange }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);

  React.useEffect(() => {
    function handle(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  function toggle(val) {
    onChange(selected.includes(val) ? selected.filter(x => x !== val) : [...selected, val]);
  }

  const displayText = selected.length === 0 ? 'Все агенты' : `Выбрано: ${selected.length}`;

  return (
    <div ref={ref} style={{ position:'relative', minWidth:150 }}>
      <button onClick={() => setOpen(v => !v)} style={{
        width:'100%', padding:'7px 12px',
        border:`1.5px solid ${open ? '#277F4B' : '#E0E0E0'}`, borderRadius:8,
        background:'#fff', fontSize:13, fontFamily:'inherit',
        color:'#333', cursor:'pointer', textAlign:'left',
        display:'flex', justifyContent:'space-between', alignItems:'center',
      }}>
        <span>{displayText}</span>
        <span style={{ fontSize:10, color:'#aaa', marginLeft:6 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div style={{
          position:'absolute', top:'calc(100% + 4px)', left:0, zIndex:200,
          background:'#fff', border:'1.5px solid #E0E0E0', borderRadius:10,
          boxShadow:'0 4px 16px rgba(0,0,0,.1)', minWidth:'100%', padding:'6px 0',
        }}>
          {options.map(opt => (
            <label key={opt.value} style={{
              display:'flex', alignItems:'center', gap:8,
              padding:'7px 14px', cursor:'pointer', fontSize:13,
              color:'#333', whiteSpace:'nowrap',
            }}
              onMouseEnter={e => e.currentTarget.style.background = '#f5f5f5'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <input type="checkbox"
                checked={selected.includes(opt.value)}
                onChange={() => toggle(opt.value)}
                style={{ accentColor:'#277F4B', width:14, height:14, cursor:'pointer' }}
              />
              {opt.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

function AdminPage({ user }) {
  const [tab, setTab] = React.useState('messages');
  return (
    <div className="admin-layout">
      <div className="admin-tabs">
        <button className={`tab-btn ${tab==='messages'?'tab-btn--active':''}`}
          onClick={() => setTab('messages')}>★ Ответы и оценки</button>
        <button className={`tab-btn ${tab==='stats'?'tab-btn--active':''}`}
          onClick={() => setTab('stats')}>📈 Статистика</button>
        <button className={`tab-btn ${tab==='users'?'tab-btn--active':''}`}
          onClick={() => setTab('users')}>👥 Пользователи</button>
      </div>
      <div className="admin-content">
        {tab==='messages' && <MessagesTab/>}
        {tab==='stats'    && <StatsTab/>}
        {tab==='users'    && <UsersTab/>}
      </div>
    </div>
  );
}

function MessagesTab() {
  const [allMessages, setAllMessages] = React.useState([]);
  const [messages,    setMessages]    = React.useState([]);
  const [loading,     setLoading]     = React.useState(false);
  const [sortBy,      setSortBy]      = React.useState('date');
  const [sortDir,     setSortDir]     = React.useState('desc');
  const [filters, setFilters] = React.useState({
    user_id:'', agents:[], rating:'',
    date_after:'', date_before:'',
    order_by:'date', order:'desc',
  });

  const AGENT_OPTIONS = [
    { value:'claims_agent',            label:'Иски и претензии' },
    { value:'general_questions_agent', label:'Общие вопросы' },
    { value:'router_agent',            label:'Маршрутизатор' },
  ];
  const RATINGS = ['','1','2','3','4','5'];

  async function load(f=filters, ob=sortBy, od=sortDir) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page:1, limit:1000, order_by:ob, order:od });
      if (f.user_id) params.append('user_id', f.user_id);
      if (f.rating)  params.append('rating',  parseInt(f.rating));
      if (f.date_after  && f.date_after.trim())  params.append('date_after',  new Date(f.date_after).toISOString());
      if (f.date_before && f.date_before.trim()) params.append('date_before', new Date(f.date_before).toISOString());

      const data = await api.get(`/admin/messages/?${params}`);
      const msgs = data.messages || [];

      // Фильтрация по агентам на фронте
      const filtered = f.agents && f.agents.length > 0
        ? msgs.filter(m => f.agents.includes(m.agent))
        : msgs;

      setAllMessages(msgs);
      setMessages(filtered);
    } catch { toast.error('Не удалось загрузить сообщения'); }
    finally { setLoading(false); }
  }

  React.useEffect(() => { load(); }, []);

  function applyFilters() { load(filters, sortBy, sortDir); }

  function resetFilters() {
    const empty = { user_id:'', agents:[], rating:'', date_after:'', date_before:'', order_by:'date', order:'desc' };
    setFilters(empty);
    setSortBy('date');
    setSortDir('desc');
    load(empty, 'date', 'desc');
  }

  function handleSort(col) {
    const newDir = sortBy === col && sortDir === 'desc' ? 'asc' : 'desc';
    setSortBy(col);
    setSortDir(newDir);
    load(filters, col, newDir);
  }

  function SortIcon({ col }) {
    if (sortBy !== col) return <span style={{color:'#ffffff', marginLeft:4}}>↕</span>;
    return <span style={{marginLeft:4}}>{sortDir === 'asc' ? '↑' : '↓'}</span>;
  }

  function fmtDate(dt) {
    if (!dt) return '—';
    return new Date(dt).toLocaleString('ru-RU', {
      day:'2-digit', month:'2-digit', year:'numeric',
      hour:'2-digit', minute:'2-digit',
    });
  }

  function StarsDisplay({ r }) {
    if (!r) return <span className="no-rating">—</span>;
    return <span className="rating-star">{'★'.repeat(r)}{'☆'.repeat(5-r)}</span>;
  }

  const COLS = [
    { key:'date',            label:'Дата' },
    { key:null,              label:'User ID' },
    { key:null,              label:'Агент' },
    { key:'processing_time', label:'Время ответа' },
    { key:null,              label:'Ответ' },
    { key:'rating',          label:'Оценка' },
    { key:'tokens',          label:'Токены' },
  ];

  return (
    <>
      <div className="filters-row">
        <div className="filter-group">
          <span className="filter-label">Оценка</span>
          <select className="filter-select" value={filters.rating}
            onChange={e => setFilters(p => ({...p, rating:e.target.value}))}>
            {RATINGS.map(r => <option key={r} value={r}>{r||'Все оценки'}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <span className="filter-label">User ID</span>
          <input className="filter-input" placeholder="User_id..." value={filters.user_id}
            onChange={e => setFilters(p => ({...p, user_id:e.target.value}))}/>
        </div>
        <div className="filter-group">
          <span className="filter-label">Агент</span>
          <MultiSelect
            options={AGENT_OPTIONS}
            selected={filters.agents}
            onChange={agents => setFilters(p => ({...p, agents}))}
          />
        </div>
        <div className="filter-group">
          <span className="filter-label">От</span>
          <input className="filter-input filter-date" type="datetime-local"
            value={filters.date_after}
            onChange={e => setFilters(p => ({...p, date_after:e.target.value}))}/>
        </div>
        <div className="filter-group">
          <span className="filter-label">До</span>
          <input className="filter-input filter-date" type="datetime-local"
            value={filters.date_before}
            onChange={e => setFilters(p => ({...p, date_before:e.target.value}))}/>
        </div>
        <button className="btn-filter-apply" onClick={applyFilters}>Применить</button>
        <button className="btn-filter-apply" style={{background:'#888'}} onClick={resetFilters}>Сбросить</button>
      </div>

      {loading && <div className="spinner"/>}

      {!loading && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {COLS.map(col => (
                  <th key={col.label}
                    onClick={() => col.key && handleSort(col.key)}
                    style={{ cursor:col.key?'pointer':'default', userSelect:'none' }}
                  >
                    {col.label}
                    {col.key && <SortIcon col={col.key}/>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {messages.map((m,i) => (
                <tr key={i}>
                  <td style={{whiteSpace:'nowrap'}}>{fmtDate(m.sending_time)}</td>
                  <td>{m.user_id}</td>
                  <td>{m.agent||'—'}</td>
                  <td>{m.processing_time!=null?`${m.processing_time} мс`:'—'}</td>
                  <td className="td-truncate" title={m.ai_message}>{m.ai_message}</td>
                  <td><StarsDisplay r={m.rating}/></td>
                  <td>{m.tokens??'—'}</td>
                </tr>
              ))}
              {messages.length===0 && (
                <tr><td colSpan={7} style={{textAlign:'center',color:'#aaa',padding:24}}>Нет данных</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function StatsTab() {
  const [ratings,      setRatings]      = React.useState([]);
  const [appeals,      setAppeals]      = React.useState([]);
  const [agentRatings, setAgentRatings] = React.useState([]);
  const [loading,      setLoading]      = React.useState(true);

  React.useEffect(() => {
    Promise.all([
      api.get('/admin/messages/ratings/'),
      api.get('/admin/appeal_types/'),
      api.get('/admin/agent-rating/'),
    ])
      .then(([r,a,ar]) => {
        setRatings(r.statistics||[]);
        setAppeals(a.statistics||[]);
        setAgentRatings(ar.statistics||[]);
      })
      .catch(() => toast.error('Не удалось загрузить статистику'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner"/>;

  const maxRating    = Math.max(...ratings.map(r=>r.amount), 1);
  const totalAppeals = appeals.reduce((s,a)=>s+a.amount,0)||1;
  const ratingColors = {5:'#277F4B',4:'#5BAD7F',3:'#A3D4B8',2:'#E07B74',1:'#C0392B'};
  const agentColor   = r => r>=4?'#277F4B':r>=3?'#5BAD7F':'#D0534A';

  return (
    <div>
      <div className="stats-grid">
        <div className="stats-card">
          <div className="stats-card-title">Типы обращений</div>
          {appeals.length===0 && <div className="empty-state">Нет данных</div>}
          {appeals.map(a => (
            <div key={a.appeal} style={{marginBottom:14}}>
              <div style={{fontSize:12,color:'#555',marginBottom:5}}>{a.appeal}</div>
              <div style={{display:'flex',alignItems:'center',gap:10}}>
                <div className="rating-bar-track" style={{flex:1}}>
                  <div className="rating-bar-fill" style={{width:`${(a.amount/totalAppeals)*100}%`,background:'#277F4B'}}/>
                </div>
                <div className="rating-bar-count">{a.amount}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="stats-card">
          <div className="stats-card-title">Распределение оценок</div>
          {[5,4,3,2,1].map(star => {
            const found = ratings.find(r=>r.rating===star);
            const amt   = found ? found.amount : 0;
            return (
              <div key={star} style={{marginBottom:14}}>
                <div style={{fontSize:12,color:'#555',marginBottom:5}}>{star} ★</div>
                <div style={{display:'flex',alignItems:'center',gap:10}}>
                  <div className="rating-bar-track" style={{flex:1}}>
                    <div className="rating-bar-fill" style={{width:`${(amt/maxRating)*100}%`,background:ratingColors[star]}}/>
                  </div>
                  <div className="rating-bar-count">{amt}</div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="stats-card" style={{gridColumn:'1/-1', width:'50%', margin:'0 auto'}}>
          <div className="stats-card-title">Оценка по агентам</div>
          {agentRatings.length===0 && <div className="empty-state">Нет данных</div>}
          {agentRatings.map(a => (
            <div key={a.agent} style={{marginBottom:14}}>
              <div style={{fontSize:12,color:'#555',marginBottom:5}}>{a.agent}</div>
              <div style={{display:'flex',alignItems:'center',gap:12}}>
                <div className="agent-bar-track" style={{flex:1}}>
                  <div className="agent-bar-fill" style={{width:`${(a.rating/5)*100}%`,background:agentColor(a.rating)}}/>
                </div>
                <div className="agent-val" style={{color:agentColor(a.rating)}}>{Number(a.rating).toFixed(1)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function UsersTab() {
  const [users,   setUsers]   = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [page,    setPage]    = React.useState(1);
  const [hasMore, setHasMore] = React.useState(true);
  const [filters, setFilters] = React.useState({ username:'', email:'', is_admin:'' });

  async function load(p=1, f=filters) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page:p, limit:20 });
      if (f.username)      params.append('username', f.username);
      if (f.email)         params.append('email',    f.email);
      if (f.is_admin!=='') params.append('is_admin', f.is_admin);
      const data = await api.get(`/admin/users/?${params}`);
      const u = data.users||[];
      setUsers(p===1 ? u : prev=>[...prev,...u]);
      setHasMore(u.length===20);
      setPage(p);
    } catch { toast.error('Не удалось загрузить пользователей'); }
    finally { setLoading(false); }
  }

  React.useEffect(() => { load(); }, []);

  return (
    <>
      <div className="filters-row">
        <div className="filter-group">
          <span className="filter-label">Username</span>
          <input className="filter-input" placeholder="Поиск..." value={filters.username}
            onChange={e=>setFilters(p=>({...p,username:e.target.value}))}/>
        </div>
        <div className="filter-group">
          <span className="filter-label">Email</span>
          <input className="filter-input" placeholder="Поиск..." value={filters.email}
            onChange={e=>setFilters(p=>({...p,email:e.target.value}))}/>
        </div>
        <div className="filter-group">
          <span className="filter-label">Роль</span>
          <select className="filter-select" value={filters.is_admin}
            onChange={e=>setFilters(p=>({...p,is_admin:e.target.value}))}>
            <option value="">Все</option>
            <option value="true">Администратор</option>
            <option value="false">Пользователь</option>
          </select>
        </div>
        <button className="btn-filter-apply" onClick={()=>load(1)}>Применить</button>
        <button className="btn-filter-apply" style={{background:'#888'}} onClick={()=>{
          const empty={username:'',email:'',is_admin:''};
          setFilters(empty); load(1,empty);
        }}>Сбросить</button>
      </div>

      {loading && users.length===0 && <div className="spinner"/>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th><th>Username</th><th>Email</th>
              <th>ФИО</th><th>Роль</th><th>Чатов</th><th>Токенов</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u=>(
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.username}</td>
                <td>{u.email}</td>
                <td>{[u.surname,u.name,u.patronymic].filter(Boolean).join(' ')}</td>
                <td>
                  <span style={{
                    padding:'2px 8px',borderRadius:10,fontSize:12,fontWeight:500,
                    background:u.is_admin?'#E8F5EE':'#f0f0f0',
                    color:u.is_admin?'#277F4B':'#666',
                  }}>
                    {u.is_admin?'Админ':'Пользователь'}
                  </span>
                </td>
                <td>{u.chats}</td>
                <td>{u.tokens}</td>
              </tr>
            ))}
            {users.length===0 && !loading && (
              <tr><td colSpan={7} style={{textAlign:'center',color:'#aaa',padding:24}}>Нет данных</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {hasMore && !loading && (
        <div style={{textAlign:'center',marginTop:12}}>
          <button className="btn-filter-apply" onClick={()=>load(page+1)}>Загрузить ещё</button>
        </div>
      )}
    </>
  );
}
