function AdminPage({ user }) {
  const [tab, setTab] = React.useState('messages');

  return (
    <div className="admin-layout">
      <div className="admin-tabs">
        <button className={`tab-btn ${tab==='messages' ? 'tab-btn--active':''}`}
          onClick={() => setTab('messages')}>★ Ответы и оценки</button>
        <button className={`tab-btn ${tab==='stats' ? 'tab-btn--active':''}`}
          onClick={() => setTab('stats')}>📈 Статистика</button>
        <button className={`tab-btn ${tab==='users' ? 'tab-btn--active':''}`}
          onClick={() => setTab('users')}>👥 Пользователи</button>
      </div>
      <div className="admin-content">
        {tab === 'messages' && <MessagesTab/>}
        {tab === 'stats'    && <StatsTab/>}
        {tab === 'users'    && <UsersTab/>}
      </div>
    </div>
  );
}

function MessagesTab() {
  const [messages, setMessages] = React.useState([]);
  const [loading, setLoading]   = React.useState(false);
  const [page, setPage]         = React.useState(1);
  const [hasMore, setHasMore]   = React.useState(true);
  const [filters, setFilters]   = React.useState({
    user_id:'', agent:'', rating:'', date_after:'', date_before:'',
    order_by:'date', order:'desc',
  });

  const AGENTS  = ['','claims_agent','general_questions_agent','router_agent'];
  const RATINGS = ['','1','2','3','4','5'];

  async function load(p=1, f=filters) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page:p, limit:20, order_by:f.order_by||'date', order:f.order||'desc' });
      if (f.user_id)     params.append('user_id',     f.user_id);
      if (f.agent)       params.append('agent',       f.agent);
      if (f.rating)      params.append('rating',      f.rating);
      if (f.date_after)  params.append('date_after',  new Date(f.date_after).toISOString());
      if (f.date_before) params.append('date_before', new Date(f.date_before).toISOString());
      const data = await api.get(`/admin/messages/?${params}`);
      const msgs = data.messages || [];
      setMessages(p===1 ? msgs : prev => [...prev, ...msgs]);
      setHasMore(msgs.length === 20);
      setPage(p);
    } catch { toast.error('Не удалось загрузить сообщения'); }
    finally { setLoading(false); }
  }

  React.useEffect(() => { load(1, {}); }, []);

  function applyFilters() { load(1, filters); }
  function resetFilters() {
    const empty = { user_id:'',agent:'',rating:'',date_after:'',date_before:'',order_by:'date',order:'desc' };
    setFilters(empty); load(1, empty);
  }

  function fmtDate(dt) {
    if (!dt) return '—';
    return new Date(dt).toLocaleString('ru-RU', {
      day:'2-digit', month:'2-digit', year:'numeric',
      hour:'2-digit', minute:'2-digit'
    });
  }

  function StarsDisplay({ r }) {
    if (!r) return <span className="no-rating">—</span>;
    return <span className="rating-star">{'★'.repeat(r)}{'☆'.repeat(5-r)}</span>;
  }

  const agentLabels = {
    claims_agent: 'claims_agent',
    general_questions_agent: 'general_questions_agent',
    router_agent: 'router_agent',
  };

  return (
    <>
      <div className="filters-row">
        <div className="filter-group">
          <span className="filter-label">Оценка</span>
          <select className="filter-select" value={filters.rating}
            onChange={e => setFilters(p=>({...p,rating:e.target.value}))}>
            {RATINGS.map(r=><option key={r} value={r}>{r||'Все оценки'}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <span className="filter-label">User ID</span>
          <input className="filter-input" placeholder="User_id..." value={filters.user_id}
            onChange={e=>setFilters(p=>({...p,user_id:e.target.value}))}/>
        </div>
        <div className="filter-group">
          <span className="filter-label">Агент</span>
          <select className="filter-select" value={filters.agent}
            onChange={e=>setFilters(p=>({...p,agent:e.target.value}))}>
            {AGENTS.map(a=><option key={a} value={a}>{a||'Все агенты'}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <span className="filter-label">От</span>
          <input className="filter-input filter-date" type="datetime-local" value={filters.date_after}
            onChange={e=>setFilters(p=>({...p,date_after:e.target.value}))}/>
        </div>
        <div className="filter-group">
          <span className="filter-label">До</span>
          <input className="filter-input filter-date" type="datetime-local" value={filters.date_before}
            onChange={e=>setFilters(p=>({...p,date_before:e.target.value}))}/>
        </div>
        <button className="btn-filter-apply" onClick={applyFilters}>Применить</button>
        <button className="btn-filter-apply" style={{background:'#888'}} onClick={resetFilters}>Сбросить</button>
      </div>

      {loading && messages.length===0 && <div className="spinner"/>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Дата</th><th>User ID</th><th>Агент</th>
              <th>Время ответа</th><th>Ответ</th><th>Оценка</th><th>Токены</th>
            </tr>
          </thead>
          <tbody>
            {messages.map((m,i)=>(
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
            {messages.length===0 && !loading && (
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
      {loading && messages.length>0 && (
        <div style={{textAlign:'center',padding:12,color:'#aaa'}}>Загрузка...</div>
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
      .catch(()=>toast.error('Не удалось загрузить статистику'))
      .finally(()=>setLoading(false));
  }, []);

  if (loading) return <div className="spinner"/>;

  const maxRating    = Math.max(...ratings.map(r=>r.amount), 1);
  const totalAppeals = appeals.reduce((s,a)=>s+a.amount,0)||1;

  const ratingColors = {5:'#277F4B',4:'#5BAD7F',3:'#A3D4B8',2:'#E07B74',1:'#C0392B'};
  const agentColor   = r => r>=4?'#277F4B':r>=3?'#5BAD7F':'#D0534A';

  return (
    <div>
      <div className="stats-grid">

        {/* Типы обращений */}
        <div className="stats-card">
          <div className="stats-card-title">Типы обращений</div>
          {appeals.length===0 && <div className="empty-state">Нет данных</div>}
          {appeals.map(a=>(
            <div key={a.appeal} style={{marginBottom:14}}>
              <div style={{fontSize:12,color:'#555',marginBottom:5}}>{a.appeal}</div>
              <div style={{display:'flex',alignItems:'center',gap:10}}>
                <div className="rating-bar-track" style={{flex:1}}>
                  <div className="rating-bar-fill"
                    style={{width:`${(a.amount/totalAppeals)*100}%`,background:'#277F4B'}}/>
                </div>
                <div className="rating-bar-count">{a.amount}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Распределение оценок */}
        <div className="stats-card">
          <div className="stats-card-title">Распределение оценок</div>
          {[5,4,3,2,1].map(star=>{
            const found = ratings.find(r=>r.rating===star);
            const amt   = found ? found.amount : 0;
            return (
              <div key={star} style={{marginBottom:14}}>
                <div style={{fontSize:12,color:'#555',marginBottom:5}}>{star} ★</div>
                <div style={{display:'flex',alignItems:'center',gap:10}}>
                  <div className="rating-bar-track" style={{flex:1}}>
                    <div className="rating-bar-fill"
                      style={{width:`${(amt/maxRating)*100}%`,background:ratingColors[star]}}/>
                  </div>
                  <div className="rating-bar-count">{amt}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Оценка по агентам */}
        <div className="stats-card" style={{gridColumn:'1/-1'}}>
          <div className="stats-card-title">Оценка по агентам</div>
          {agentRatings.length===0 && <div className="empty-state">Нет данных</div>}
          {agentRatings.map(a=>(
            <div key={a.agent} style={{marginBottom:14}}>
              <div style={{fontSize:12,color:'#555',marginBottom:5}}>{a.agent}</div>
              <div style={{display:'flex',alignItems:'center',gap:12}}>
                <div className="agent-bar-track" style={{flex:1}}>
                  <div className="agent-bar-fill"
                    style={{width:`${(a.rating/5)*100}%`,background:agentColor(a.rating)}}/>
                </div>
                <div className="agent-val" style={{color:agentColor(a.rating)}}>
                  {Number(a.rating).toFixed(1)}
                </div>
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
      if (f.username) params.append('username', f.username);
      if (f.email)    params.append('email',    f.email);
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
                    padding:'2px 8px', borderRadius:10, fontSize:12, fontWeight:500,
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
