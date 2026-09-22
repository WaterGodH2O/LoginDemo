import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Form, Input, Typography, message } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()

  const onFinish = (values) => {
    const username = values.username.trim()

    // 校验通过后向后端 POST 登录请求，由服务器核对账号密码。
    // 请求体：{ username, password }
    // username 为去掉首尾空格后的用户名；password 为输入框原值 values.password，不去空格。
    // 核对成功后再提示并跳转；失败则留在登录页显示错误。
    // 明文传输先用着，后面再改。


    message.success(`欢迎回来，${username}`)
    
    navigate('/home', { state: { username } })
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
              prefix={<UserOutlined />}
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
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 12 }}>
            <Button type="primary" htmlType="submit" size="large" block>
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
