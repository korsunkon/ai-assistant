import React from "react";
import { Layout, Menu } from "antd";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import {
  DatabaseOutlined,
  ExperimentOutlined,
  TableOutlined,
} from "@ant-design/icons";
import { CallsPage } from "./pages/CallsPage";
import { NewAnalysisPage } from "./pages/NewAnalysisPage";
import { AnalysisResultsPage } from "./pages/AnalysisResultsPage";
import { AnalysisStatusPage } from "./pages/AnalysisStatusPage";
import { AnalysesListPage } from "./pages/AnalysesListPage";

const { Header, Sider, Content } = Layout;

const AppLayout: React.FC = () => {
  const location = useLocation();

  const selectedKey = React.useMemo(() => {
    if (location.pathname.startsWith("/calls")) return "calls";
    if (location.pathname.startsWith("/analysis/new")) return "new-analysis";
    if (location.pathname.match(/^\/analysis\/\d+\/status$/)) return "new-analysis";
    if (location.pathname.startsWith("/analysis")) return "results";
    return "calls";
  }, [location.pathname]);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider theme="light">
        <div
          style={{
            height: 48,
            margin: 16,
            fontWeight: 600,
            fontSize: 16,
          }}
        >
          AI Ассистент
        </div>
        <Menu mode="inline" selectedKeys={[selectedKey]}>
          <Menu.Item key="calls" icon={<DatabaseOutlined />}>
            <Link to="/calls">Звонки</Link>
          </Menu.Item>
          <Menu.Item key="new-analysis" icon={<ExperimentOutlined />}>
            <Link to="/analysis/new">Новое исследование</Link>
          </Menu.Item>
          <Menu.Item key="results" icon={<TableOutlined />}>
            <Link to="/analysis">Результаты</Link>
          </Menu.Item>
        </Menu>
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            paddingInline: 24,
            display: "flex",
            alignItems: "center",
          }}
        >
          <h2 style={{ margin: 0 }}>AI Ассистент Маркетолога</h2>
        </Header>
        <Content style={{ margin: 24 }}>
          <Routes>
            <Route path="/calls" element={<CallsPage />} />
            <Route path="/analysis/new" element={<NewAnalysisPage />} />
            <Route path="/analysis" element={<AnalysesListPage />} />
            <Route path="/analysis/:id" element={<AnalysisResultsPage />} />
            <Route path="/analysis/:id/status" element={<AnalysisStatusPage />} />
            <Route path="*" element={<CallsPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => {
  return <AppLayout />;
};

export default App;


