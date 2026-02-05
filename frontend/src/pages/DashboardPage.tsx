import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Typography,
  Spin,
  Select,
  Space,
  Button,
  message,
  Progress,
  Empty,
  Tooltip,
} from "antd";
import {
  WarningOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import { api, DashboardData, Incident } from "../api/client";

const { Title, Text } = Typography;

export const DashboardPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadDashboard();
    }
  }, [id]);

  const loadDashboard = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const dashboardData = await api.getAnalysisDashboard(parseInt(id));
      setData(dashboardData);
    } catch (error: any) {
      message.error(error.response?.data?.detail || "Ошибка загрузки данных");
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "red";
      case "medium":
        return "orange";
      case "low":
        return "gold";
      default:
        return "default";
    }
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case "high":
        return "Высокая";
      case "medium":
        return "Средняя";
      case "low":
        return "Низкая";
      case "none":
        return "Нет";
      default:
        return severity;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case "verbal_aggression":
        return "Вербальная агрессия";
      case "conflict":
        return "Конфликт";
      case "physical":
        return "Физическая агрессия";
      default:
        return type;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "verbal_aggression":
        return "volcano";
      case "conflict":
        return "orange";
      case "physical":
        return "red";
      default:
        return "default";
    }
  };

  // Фильтрация инцидентов
  const filteredIncidents = React.useMemo(() => {
    if (!data) return [];
    let incidents = data.incidents;

    if (filterType) {
      incidents = incidents.filter((i) => i.type === filterType);
    }
    if (filterSeverity) {
      incidents = incidents.filter((i) => i.severity === filterSeverity);
    }

    return incidents;
  }, [data, filterType, filterSeverity]);

  // Уникальные типы и уровни для фильтров
  const uniqueTypes = React.useMemo(() => {
    if (!data) return [];
    return [...new Set(data.incidents.map((i) => i.type))];
  }, [data]);

  // Экспорт в CSV
  const exportToCSV = () => {
    if (!data) return;

    const headers = ["Файл", "Время начала", "Время конца", "Тип", "Уровень", "Описание", "Цитата"];
    const rows = filteredIncidents.map((i) => [
      i.filename,
      formatTime(i.start_time),
      formatTime(i.end_time),
      getTypeLabel(i.type),
      getSeverityLabel(i.severity),
      i.description,
      i.quote,
    ]);

    const csvContent =
      headers.join(",") +
      "\n" +
      rows
        .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
        .join("\n");

    const blob = new Blob(["\ufeff" + csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `incidents_analysis_${id}.csv`;
    link.click();
    message.success("CSV файл скачан");
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return <Empty description="Данные не найдены" />;
  }

  const { stats } = data;
  const incidentRate = stats.total_files > 0
    ? Math.round((stats.files_with_incidents / stats.total_files) * 100)
    : 0;

  const columns = [
    {
      title: "Файл",
      dataIndex: "filename",
      key: "filename",
      width: 200,
      ellipsis: true,
      render: (text: string, record: Incident) => (
        <Button
          type="link"
          icon={<FileTextOutlined />}
          onClick={() => navigate(`/analysis/${id}`)}
          style={{ padding: 0 }}
        >
          {text}
        </Button>
      ),
    },
    {
      title: "Время",
      key: "time",
      width: 120,
      render: (_: any, record: Incident) => (
        <Space>
          <ClockCircleOutlined />
          <Text>{formatTime(record.start_time)} - {formatTime(record.end_time)}</Text>
        </Space>
      ),
    },
    {
      title: "Тип",
      dataIndex: "type",
      key: "type",
      width: 180,
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>{getTypeLabel(type)}</Tag>
      ),
    },
    {
      title: "Уровень",
      dataIndex: "severity",
      key: "severity",
      width: 120,
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{getSeverityLabel(severity)}</Tag>
      ),
    },
    {
      title: "Описание",
      dataIndex: "description",
      key: "description",
      width: 300,
      render: (text: string) => (
        <Tooltip title={text} placement="topLeft" overlayStyle={{ maxWidth: 400 }}>
          <Text style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            cursor: 'pointer'
          }}>
            {text}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: "Цитата",
      dataIndex: "quote",
      key: "quote",
      width: 280,
      render: (text: string) => text ? (
        <Tooltip title={`"${text}"`} placement="topLeft" overlayStyle={{ maxWidth: 400 }}>
          <Text italic style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            cursor: 'pointer'
          }}>
            "{text}"
          </Text>
        </Tooltip>
      ) : "-",
    },
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        {/* Заголовок */}
        <div>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(`/analysis/${id}`)}
            style={{ marginBottom: 16 }}
          >
            К результатам
          </Button>
          <Title level={2}>
            <AlertOutlined style={{ marginRight: 8 }} />
            Dashboard: {data.analysis_name}
          </Title>
        </div>

        {/* Основная статистика */}
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Всего файлов"
                value={stats.total_files}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Файлов с инцидентами"
                value={stats.files_with_incidents}
                valueStyle={{ color: stats.files_with_incidents > 0 ? "#cf1322" : "#3f8600" }}
                prefix={<WarningOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Всего инцидентов"
                value={stats.total_incidents}
                valueStyle={{ color: "#cf1322" }}
                prefix={<AlertOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Процент с инцидентами"
                value={incidentRate}
                suffix="%"
                valueStyle={{ color: incidentRate > 20 ? "#cf1322" : "#3f8600" }}
              />
            </Card>
          </Col>
        </Row>

        {/* Распределение по типам и уровням */}
        <Row gutter={16}>
          <Col span={12}>
            <Card title="По типам инцидентов">
              {Object.entries(stats.incidents_by_type).length > 0 ? (
                <Space direction="vertical" style={{ width: "100%" }}>
                  {Object.entries(stats.incidents_by_type).map(([type, count]) => (
                    <div key={type} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <Tag color={getTypeColor(type)}>{getTypeLabel(type)}</Tag>
                      <div style={{ flex: 1, margin: "0 16px" }}>
                        <Progress
                          percent={Math.round((count / stats.total_incidents) * 100)}
                          size="small"
                          strokeColor={getTypeColor(type) === "red" ? "#ff4d4f" : "#fa8c16"}
                        />
                      </div>
                      <Text strong>{count}</Text>
                    </div>
                  ))}
                </Space>
              ) : (
                <Empty description="Нет данных" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Col>
          <Col span={12}>
            <Card title="По уровню серьёзности">
              <Space direction="vertical" style={{ width: "100%" }}>
                {["high", "medium", "low", "none"].map((severity) => {
                  const count = stats.severity_distribution[severity] || 0;
                  const percent = stats.total_files > 0 ? Math.round((count / stats.total_files) * 100) : 0;
                  return (
                    <div key={severity} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <Tag color={getSeverityColor(severity)}>{getSeverityLabel(severity)}</Tag>
                      <div style={{ flex: 1, margin: "0 16px" }}>
                        <Progress
                          percent={percent}
                          size="small"
                          strokeColor={severity === "high" ? "#ff4d4f" : severity === "medium" ? "#fa8c16" : "#52c41a"}
                        />
                      </div>
                      <Text strong>{count} файлов</Text>
                    </div>
                  );
                })}
              </Space>
            </Card>
          </Col>
        </Row>

        {/* Таблица инцидентов */}
        <Card
          title={`Список инцидентов (${filteredIncidents.length})`}
          extra={
            <Space>
              <Select
                placeholder="Тип"
                allowClear
                style={{ width: 180 }}
                value={filterType}
                onChange={setFilterType}
              >
                {uniqueTypes.map((type) => (
                  <Select.Option key={type} value={type}>
                    {getTypeLabel(type)}
                  </Select.Option>
                ))}
              </Select>
              <Select
                placeholder="Уровень"
                allowClear
                style={{ width: 120 }}
                value={filterSeverity}
                onChange={setFilterSeverity}
              >
                <Select.Option value="high">Высокая</Select.Option>
                <Select.Option value="medium">Средняя</Select.Option>
                <Select.Option value="low">Низкая</Select.Option>
              </Select>
              <Button icon={<DownloadOutlined />} onClick={exportToCSV}>
                Экспорт CSV
              </Button>
            </Space>
          }
        >
          {filteredIncidents.length > 0 ? (
            <Table
              columns={columns}
              dataSource={filteredIncidents}
              rowKey={(record, index) => `${record.file_id}-${index}`}
              pagination={{ pageSize: 20 }}
              scroll={{ x: 1300 }}
            />
          ) : (
            <Empty
              description={
                stats.total_incidents === 0
                  ? "Инциденты не обнаружены"
                  : "Нет инцидентов по выбранным фильтрам"
              }
              image={
                stats.total_incidents === 0 ? (
                  <CheckCircleOutlined style={{ fontSize: 64, color: "#52c41a" }} />
                ) : (
                  Empty.PRESENTED_IMAGE_SIMPLE
                )
              }
            />
          )}
        </Card>
      </Space>
    </div>
  );
};
