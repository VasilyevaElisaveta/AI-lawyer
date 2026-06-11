const Auth = {
  getAccess()  { return localStorage.getItem('access_token'); },
  getRefresh() { return localStorage.getItem('refresh_token'); },
  save(access, refresh) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  },
  clear() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
  saveUser(user) { localStorage.setItem('user', JSON.stringify(user)); },
  getUser()  { try { return JSON.parse(localStorage.getItem('user')); } catch { return null; } },
  isLoggedIn() { return !!Auth.getAccess(); },
};
