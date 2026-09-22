import { Layout, Menu, Typography } from 'antd'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'

const { Header, Content } = Layout

const items = [
  { key: 'home', label: '首页' },
  { key: 'login', label: '登录' },
  { key: 'register', label: '注册' },
]

const pathToKey = {
  '/home': 'home',
  '/login': 'login',
  '/register': 'register',
}

const keyToPath = {
  home: '/home',
  login: '/login',
  register: '/register',
}

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()

  // 测试时暂时总是保留顶栏，方便切换页面


  // if (location.pathname === '/login') {
  //   return <Login />
  // }

  // if (location.pathname === '/register') {
  //   return <Register />
  // }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <Typography.Text style={{ color: '#fff', whiteSpace: 'nowrap' }}>
          切换（测试用）
        </Typography.Text>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[pathToKey[location.pathname] ?? 'home']}
          items={items}
          onClick={({ key }) => navigate(keyToPath[key])}
          style={{ flex: 1, minWidth: 0 }}
        />
      </Header>
      <Content style={{ padding: 32, maxWidth: 720 }}>
        <Typography.Paragraph type="secondary">
          当前路径：<strong>{location.pathname}</strong>
          （切换组件，页面没有刷新）
        </Typography.Paragraph>
        <Routes>
          <Route path="/home" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Navigate to="/home" replace />} />
        </Routes>
      </Content>
    </Layout>
  )
}
