import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, theme } from 'antd'
import {
  DashboardOutlined,
  BookOutlined,
  FileTextOutlined,
  SettingOutlined,
  NodeIndexOutlined,
  FormOutlined,
  ScanOutlined,
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/knowledge',
    icon: <NodeIndexOutlined />,
    label: '知识点管理',
  },
  {
    key: '/questions',
    icon: <BookOutlined />,
    label: '题库管理',
  },
  {
    key: '/questions/file-import',
    icon: <ScanOutlined />,
    label: '文件导入中心',
  },
  {
    key: '/templates',
    icon: <FormOutlined />,
    label: '试卷模板',
  },
  {
    key: '/generator',
    icon: <FileTextOutlined />,
    label: '生成试卷',
  },
  {
    key: '/papers',
    icon: <FileTextOutlined />,
    label: '历史试卷',
  },
]

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={200}
      >
        <div
          style={{
            height: 32,
            margin: 16,
            background: 'rgba(255, 255, 255, 0.2)',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 'bold',
            fontSize: collapsed ? 12 : 14,
          }}
        >
          {collapsed ? 'MPF' : 'MathPaperForge'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <h2 style={{ margin: 0, fontSize: 18 }}>数学试卷智能生成系统</h2>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
