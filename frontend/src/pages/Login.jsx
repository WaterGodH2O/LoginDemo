import { useState } from 'react'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Form, Input, Typography, message } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api.js'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)

  const onFinish = async (values) => {
    const username = values.username.trim()
    const password = values.password

    setSubmitting(true)
    try {
      const res = await api.post('/api/login', {
        username,
        password,
      })
      const name = res.data.username || username
      message.success(res.data.message || `欢迎回来，${name}`)
      navigate('/home')
    } catch (error) {
      const text = error.response?.data?.message || '登录失败，请确认后端已启动'
      message.error(text)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <section className="login-card">
        <div className="login-mark" aria-hidden="true">
          <UserOutlined />
        </div>
        <Typography.Title level={3} className="login-title">
          登录
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="login-subtitle">
          使用用户名和密码进入系统
        </Typography.Paragraph>
        <Form
          layout="vertical"
          requiredMark={false}
          onFinish={onFinish}
          autoComplete="off"
        >
          <Form.Item
            label="用户名"
            name="username"
            rules={[
              {
                validator: (_, value) => {
                  const name = typeof value === 'string' ? value.trim() : ''
                  if (!name) {
                    return Promise.reject(new Error('请输入用户名'))
                  }
                  return Promise.resolve()
                },
              },
            ]}
          >
            <Input
              size="large"
              prefix={<UserOutlined />}
              placeholder="请输入用户名"
              allowClear
              autoComplete="username"
            />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              size="large"
              prefix={<LockOutlined />}
              placeholder="请输入密码"
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 12 }}>
            <Button type="primary" htmlType="submit" size="large" block loading={submitting}>
              登录
            </Button>
          </Form.Item>
        </Form>
        <div className="login-footer">
          没有账号？<Link to="/register">去注册</Link>
        </div>
      </section>
    </div>
  )
}
