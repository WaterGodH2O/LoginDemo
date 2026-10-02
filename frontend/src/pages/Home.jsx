import { Button, Typography } from 'antd'
import { Link, useLocation, useNavigate } from 'react-router-dom'

export default function Home() {
  const navigate = useNavigate()
  const location = useLocation()
  const username = location.state?.username

  return (
    <div>
      <Typography.Title level={3}>首页</Typography.Title>
      <Typography.Paragraph>
        {username ? `欢迎回来，${username}` : '尚未登录。可从登录页进入。'}
      </Typography.Paragraph>
      <Typography.Paragraph>
        地址栏是 <Typography.Text code>/home</Typography.Text>
      </Typography.Paragraph>
      <Typography.Paragraph>
        代码跳转，效果和点链接一样：
      </Typography.Paragraph>
      <Button type="primary" onClick={() => navigate('/login')}>
        去登录
      </Button>
      <div style={{ marginTop: 16 }}>
        <Link to="/register">去注册页</Link>
      </div>
    </div>
  )
}
