import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Card, Typography, Tag, Button, Space, message } from "antd";
import { EyeOutlined } from "@ant-design/icons";
import { api, Analysis } from "../api/client";

const { Title } = Typography;

export const AnalysesListPage: React.FC = () => {
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    setLoading(true);
    try {
      const data = await api.listAnalyses();
      setAnalyses(data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || "Ошибка загрузки исследований");
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 80,
    },
    {
      title: "Название",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Запрос",
      dataIndex: "query_text",
      key: "query_text",
      ellipsis: true,
      render: (text: string) => text.substring(0, 100) + (text.length > 100 ? "..." : ""),
    },
    {
      title: "Статус",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status: string) => {
        const colors: Record<string, string> = {
          completed: "green",
          running: "blue",
          pending: "default",
          error: "red",
        };
        return <Tag color={colors[status] || "default"}>{status}</Tag>;
      },
    },
    {
      title: "Прогресс",
      dataIndex: "progress",
      key: "progress",
      width: 100,
      render: (progress: number) => `${progress}%`,
    },
    {
      title: "Дата",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: "Действия",
      key: "actions",
      width: 120,
      render: (_: any, record: Analysis) => (
        <Button
          icon={<EyeOutlined />}
          onClick={() => {
            if (record.status === "completed") {
              navigate(`/analysis/${record.id}`);
            } else {
              navigate(`/analysis/${record.id}/status`);
            }
          }}
        >
          Открыть
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        <div>
          <Title level={2}>История исследований</Title>
          <Button onClick={loadAnalyses} style={{ marginBottom: 16 }}>
            Обновить
          </Button>
        </div>

        <Card>
          <Table
            columns={columns}
            dataSource={analyses}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 20 }}
          />
        </Card>
      </Space>
    </div>
  );
};

