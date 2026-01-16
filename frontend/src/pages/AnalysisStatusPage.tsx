import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Progress,
  Typography,
  Space,
  Button,
  Statistic,
  Row,
  Col,
  Spin,
  message,
} from "antd";
import { CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { api } from "../api/client";

const { Title, Text } = Typography;

export const AnalysisStatusPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AnalysisStatusPage.tsx:26','message':'useEffect triggered','data':{id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
    if (id) {
      loadStatus();
      const interval = setInterval(loadStatus, 2000); // опрос каждые 2 секунды
      return () => clearInterval(interval);
    }
  }, [id]);

  const loadStatus = async () => {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AnalysisStatusPage.tsx:34','message':'loadStatus called','data':{id},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion
    if (!id) return;
    try {
      const data = await api.getAnalysisStatus(parseInt(id));
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AnalysisStatusPage.tsx:38','message':'status loaded','data':{status:data.status,progress:data.progress,total_calls:data.total_calls,processed_calls:data.processed_calls,error_count:data.error_count},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion
      setStatus(data);
      setLoading(false);

      // Если анализ завершён — перенаправляем на результаты
      if (data.status === "completed") {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AnalysisStatusPage.tsx:45','message':'analysis completed, navigating','data':{targetUrl:`/analysis/${id}`},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        setTimeout(() => {
          navigate(`/analysis/${id}`);
        }, 2000);
      }
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AnalysisStatusPage.tsx:50','message':'loadStatus error','data':{error:error instanceof Error?error.message:'unknown'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion
      message.error("Ошибка загрузки статуса");
      setLoading(false);
    }
  };

  if (loading && !status) {
    return (
      <div style={{ textAlign: "center", padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!status) {
    return <div>Исследование не найдено</div>;
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case "completed":
        return <CheckCircleOutlined style={{ color: "#52c41a", fontSize: 48 }} />;
      case "running":
        return <ClockCircleOutlined style={{ color: "#1890ff", fontSize: 48 }} />;
      case "error":
        return <CloseCircleOutlined style={{ color: "#ff4d4f", fontSize: 48 }} />;
      default:
        return <ClockCircleOutlined style={{ fontSize: 48 }} />;
    }
  };

  const getStatusText = () => {
    switch (status.status) {
      case "completed":
        return "Завершено";
      case "running":
        return "В процессе";
      case "error":
        return "Ошибка";
      case "pending":
        return "Ожидание";
      default:
        return status.status;
    }
  };

  return (
    <div>
      <Title level={2}>Статус исследования</Title>
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        <Card>
          <Space direction="vertical" style={{ width: "100%" }} align="center" size="large">
            {getStatusIcon()}
            <Title level={3}>{getStatusText()}</Title>
            <Progress
              percent={status.progress || 0}
              status={status.status === "error" ? "exception" : "active"}
              style={{ width: "80%", maxWidth: 600 }}
            />
          </Space>
        </Card>

        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic title="Всего звонков" value={status.total_calls || 0} />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic title="Обработано" value={status.processed_calls || 0} />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Ошибки"
                value={status.error_count || 0}
                valueStyle={{ color: status.error_count > 0 ? "#cf1322" : undefined }}
              />
            </Card>
          </Col>
        </Row>

        {status.status === "completed" && (
          <Card>
            <Space direction="vertical" style={{ width: "100%" }} align="center">
              <Text>Анализ завершён! Переход к результатам...</Text>
              <Button type="primary" onClick={() => navigate(`/analysis/${id}`)}>
                Посмотреть результаты
              </Button>
            </Space>
          </Card>
        )}
      </Space>
    </div>
  );
};

