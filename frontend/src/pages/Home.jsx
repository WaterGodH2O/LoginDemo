import { Button, Typography } from 'antd'
import { Link, useNavigate } from 'react-router-dom'

export default function Home() {
  const navigate = useNavigate()

  return (
    <div>
      <Typography.Title level={3}>首页</Typography.Title>
      <Typography.Paragraph>
        这是当前显示的组件。地址栏是 <Typography.Text code>/</Typography.Text>
      </Typography.Paragraph>
      <Typography.Paragraph>
        代码跳转，效果和点链接一样：
      </Typography.Paragraph>
      <Button type="primary" onClick={() => navigate('/login')}>
        模拟登录成功后的跳转
      </Button>
      <div style={{ marginTop: 16 }}>
        <Link to="/register">去注册页</Link>
      </div>
    </div>
  )
}
