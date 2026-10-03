import { useEffect, useState } from 'react'
import { UserOutlined } from '@ant-design/icons'
import { Button, Descriptions, Empty, Space, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { fetchMe, logout } from '../auth.js'
import './Home.css'

export default function Home() {
  const navigate = useNavigate()
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const loggedIn = Boolean(session?.username)

  useEffect(() => {
    let cancelled = false
    fetchMe().then((data) => {
      if (!cancelled) {
        setSession(data)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleLogout() {
    try {
      await logout()
    } catch {
      message.error('退出失败，请确认后端已启动')
      return
    }
    setSession(null)
  }

  return (
    <div className="home-page">
      <section className="home-panel">
        <Typography.Title level={3} className="home-title">
          工作台
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="home-desc">
          样板空页面。
        </Typography.Paragraph>

        <Descriptions
          bordered
          size="middle"
          column={1}
          title="账号信息"
          extra={
            loading ? (
              <Tag>检查中</Tag>
            ) : loggedIn ? (
              <Tag color="success">已登录</Tag>
            ) : (
              <Tag>未登录</Tag>
            )
          }
        >
          <Descriptions.Item label="登录状态">
            {loading ? '检查中' : loggedIn ? '已登录' : '未登录'}
          </Descriptions.Item>
          <Descriptions.Item label="用户名">
            {session?.username || '—'}
          </Descriptions.Item>
          <Descriptions.Item label="登录时间">
            {session?.loggedInAt || '—'}
          </Descriptions.Item>
        </Descriptions>

        <div className="home-empty">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={loggedIn ? '暂无业务数据' : '登录后显示账号数据'}
          />
        </div>

        <Space>
          {loggedIn ? (
            <Button onClick={handleLogout}>退出登录</Button>
          ) : (
            <Button type="primary" icon={<UserOutlined />} onClick={() => navigate('/login')}>
              去登录
            </Button>
          )}
        </Space>
      </section>
    </div>
  )
}
