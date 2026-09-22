import { LockOutlined, UserAddOutlined } from '@ant-design/icons'
import { Button, Form, Input, Typography, message } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import './Login.css'

export default function Register() {
  const navigate = useNavigate()

  const onFinish = () => {
    message.success('注册成功，请登录')
    navigate('/login')
  }

  return (
    <div className="login-page">
      <section className="login-card">
        <div className="login-mark" aria-hidden="true">
          <UserAddOutlined />
        </div>
        <Typography.Title level={3} className="login-title">
          注册
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="login-subtitle">
          创建账号后即可登录
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
                  if (name.length < 6) {
                    return Promise.reject(new Error('用户名至少 6 位'))
                  }
                  return Promise.resolve()
                },
              },
            ]}
          >
            <Input
              size="large"
              prefix={<UserAddOutlined />}
              placeholder="至少 6 位"
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
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item
            label="确认密码"
            name="confirm"
            dependencies={['password']}
            rules={[
              { required: true, message: '请再次输入密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password
              size="large"
              prefix={<LockOutlined />}
              placeholder="请再次输入密码"
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 12 }}>
            <Button type="primary" htmlType="submit" size="large" block>
              注册
            </Button>
          </Form.Item>
        </Form>
        <div className="login-footer">
          已有账号？<Link to="/login">去登录</Link>
        </div>
      </section>
    </div>
  )
}
