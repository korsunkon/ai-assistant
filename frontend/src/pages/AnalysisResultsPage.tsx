import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Table,
  Card,
  Typography,
  Button,
  Space,
  message,
  Tag,
  Spin,
  Descriptions,
  Modal,
  Timeline,
  Divider,
} from "antd";
import { DownloadOutlined, ArrowLeftOutlined, FileTextOutlined, DashboardOutlined } from "@ant-design/icons";
import { api } from "../api/client";

const { Title } = Typography;

export const AnalysisResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [analysisInfo, setAnalysisInfo] = useState<any>(null);
  const [transcriptModalVisible, setTranscriptModalVisible] = useState(false);
  const [selectedTranscript, setSelectedTranscript] = useState<any>(null);
  const [loadingTranscript, setLoadingTranscript] = useState(false);
  const [exportingCSV, setExportingCSV] = useState(false);

  useEffect(() => {
    if (id) {
      loadResults();
      loadAnalysisInfo();
    }
  }, [id]);

  const loadAnalysisInfo = async () => {
    if (!id) return;
    try {
      const data = await api.getAnalysisStatus(parseInt(id));
      setAnalysisInfo(data);
    } catch (error) {
      console.error("Ошибка загрузки информации об исследовании");
    }
  };

  const loadResults = async () => {
    if (!id) return;
    try {
      const data = await api.getAnalysisResults(parseInt(id));
      setResults(data);
      setLoading(false);
    } catch (error: any) {
      message.error(error.response?.data?.detail || "Ошибка загрузки результатов");
      setLoading(false);
    }
  };

  const showTranscript = async (callId: number) => {
    setLoadingTranscript(true);
    setTranscriptModalVisible(true);
    try {
      const transcript = await api.getCallTranscript(callId);
      setSelectedTranscript(transcript);
    } catch (error: any) {
      message.error(error.response?.data?.detail || "Ошибка загрузки транскрипта");
      setTranscriptModalVisible(false);
    } finally {
      setLoadingTranscript(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Форматирование транскрипта с тайм-кодами для CSV
  const formatTranscriptForCSV = (transcript: any): string => {
    if (!transcript || !transcript.segments || transcript.segments.length === 0) {
      return transcript?.text || "";
    }

    return transcript.segments
      .map((segment: any) => {
        const time = formatTime(segment.start);
        const speaker = segment.role || segment.speaker || "Спикер";
        const text = segment.text || "";
        return `[${time}] ${speaker}: ${text}`;
      })
      .join("\n");
  };

  const exportToCSV = async () => {
    if (results.length === 0) {
      message.warning("Нет данных для экспорта");
      return;
    }

    setExportingCSV(true);
    message.loading({ content: "Загрузка транскрипций...", key: "csvExport", duration: 0 });

    try {
      // Загружаем транскрипции для всех файлов
      const transcripts: Record<number, any> = {};

      for (let i = 0; i < results.length; i++) {
        const result = results[i];
        message.loading({
          content: `Загрузка транскрипций: ${i + 1}/${results.length}`,
          key: "csvExport",
          duration: 0
        });

        try {
          const transcript = await api.getCallTranscript(result.call_id);
          transcripts[result.call_id] = transcript;
        } catch {
          // Если транскрипт недоступен, оставляем пустым
          transcripts[result.call_id] = null;
        }
      }

      const headers = ["Файл", "Краткая выжимка", "Транскрипция"];
      const rows = results.map((r) => [
        r.filename || "",
        r.summary || "",
        formatTranscriptForCSV(transcripts[r.call_id]),
      ]);

      const csvContent =
        "\ufeff" + // BOM для корректного отображения UTF-8 в Excel
        headers.join(";") + // Используем ; для Excel
        "\n" +
        rows
          .map((row) =>
            row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(";")
          )
          .join("\n");

      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", `analysis_${id}_results.csv`);
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      message.success({ content: "CSV файл скачан", key: "csvExport" });
    } catch (error) {
      message.error({ content: "Ошибка при экспорте", key: "csvExport" });
    } finally {
      setExportingCSV(false);
    }
  };

  const columns = [
    {
      title: "Название файла",
      dataIndex: "filename",
      key: "filename",
      width: 250,
    },
    {
      title: "Краткая выжимка",
      dataIndex: "summary",
      key: "summary",
      ellipsis: true,
      width: 300,
    },
    {
      title: "Детали",
      key: "details",
      width: 300,
      render: (_: any, record: any) => {
        try {
          const jsonData = JSON.parse(record.json_result || "{}");
          const findings = jsonData.findings || [];
          return (
            <Space direction="vertical" size="small">
              {findings.slice(0, 3).map((f: any, idx: number) => (
                <Tag key={idx}>
                  {f.criterion}: {f.value}
                </Tag>
              ))}
              {findings.length > 3 && <Tag>+{findings.length - 3} ещё</Tag>}
            </Space>
          );
        } catch {
          return <Tag>Нет данных</Tag>;
        }
      },
    },
    {
      title: "Транскрипция",
      key: "transcript",
      width: 150,
      render: (_: any, record: any) => (
        <Button
          type="primary"
          icon={<FileTextOutlined />}
          onClick={() => showTranscript(record.call_id)}
        >
          Открыть
        </Button>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        <div>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/analysis/new")} style={{ marginBottom: 16 }}>
            Назад
          </Button>
          <Title level={2}>Результаты исследования</Title>
          {analysisInfo && (
            <Descriptions bordered style={{ marginBottom: 24 }}>
              <Descriptions.Item label="Статус">
                <Tag color={analysisInfo.status === "completed" ? "green" : "blue"}>
                  {analysisInfo.status === "completed" ? "Завершено" : analysisInfo.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Прогресс">
                {analysisInfo.progress}%
              </Descriptions.Item>
              <Descriptions.Item label="Обработано звонков">
                {analysisInfo.processed_calls} / {analysisInfo.total_calls}
              </Descriptions.Item>
            </Descriptions>
          )}
        </div>

        <Card
          title={`Результаты (${results.length} звонков)`}
          extra={
            <Space>
              <Button
                type="primary"
                icon={<DashboardOutlined />}
                onClick={() => navigate(`/analysis/${id}/dashboard`)}
              >
                Dashboard
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={exportToCSV}
                loading={exportingCSV}
              >
                Экспорт CSV
              </Button>
            </Space>
          }
        >
          <Table
            columns={columns}
            dataSource={results}
            rowKey="id"
            pagination={{ pageSize: 20 }}
            scroll={{ x: 1000 }}
          />
        </Card>
      </Space>

      <Modal
        title={<span><FileTextOutlined /> Транскрипция сессии</span>}
        open={transcriptModalVisible}
        onCancel={() => {
          setTranscriptModalVisible(false);
          setSelectedTranscript(null);
        }}
        footer={null}
        width={900}
        style={{ top: 20 }}
        styles={{ body: { maxHeight: "80vh", overflowY: "auto" } }}
      >
        {loadingTranscript ? (
          <div style={{ textAlign: "center", padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : selectedTranscript ? (
          <div>
            {/* Информация о диаризации */}
            {selectedTranscript.num_speakers && selectedTranscript.num_speakers > 0 && (
              <Card size="small" style={{ marginBottom: 16, backgroundColor: "#e6f7ff" }}>
                <Space direction="vertical" style={{ width: "100%" }}>
                  <div>
                    <Typography.Text strong>Количество говорящих: </Typography.Text>
                    <Tag color="blue">{selectedTranscript.num_speakers}</Tag>
                  </div>
                  {selectedTranscript.speaker_roles && Object.keys(selectedTranscript.speaker_roles).length > 0 && (
                    <div>
                      <Typography.Text strong>Роли участников:</Typography.Text>
                      <div style={{ marginTop: 8 }}>
                        {Object.entries(selectedTranscript.speaker_roles).map(([speaker, role]: [string, any]) => (
                          <Tag key={speaker} color="gold" style={{ marginBottom: 4 }}>
                            {speaker}: {role}
                          </Tag>
                        ))}
                      </div>
                    </div>
                  )}
                </Space>
              </Card>
            )}

            <Card size="small" style={{ marginBottom: 16, backgroundColor: "#f5f5f5" }}>
              <Typography.Paragraph strong>Полный текст:</Typography.Paragraph>
              <Typography.Paragraph>{selectedTranscript.text}</Typography.Paragraph>
            </Card>

            <Divider>Детальная транскрипция с диаризацией</Divider>

            <Timeline
              items={selectedTranscript.segments?.map((segment: any, idx: number) => {
                // Определяем цвет по speaker_id для визуального различия
                const speakerColors = ["blue", "green", "orange", "purple", "cyan", "magenta"];
                const speakerId = segment.speaker_id ?? idx % 2;
                const timelineColor = speakerColors[speakerId % speakerColors.length];

                return {
                  color: timelineColor,
                  children: (
                    <div key={idx}>
                      <Space wrap>
                        <Tag color="blue">{formatTime(segment.start)}</Tag>
                        <Tag color="green">{formatTime(segment.end)}</Tag>
                        {segment.speaker && (
                          <Tag color={timelineColor}>{segment.speaker}</Tag>
                        )}
                        {segment.role && (
                          <Tag color="gold">{segment.role}</Tag>
                        )}
                      </Space>
                      <Typography.Paragraph style={{ marginTop: 8, marginBottom: 0 }}>
                        {segment.text}
                      </Typography.Paragraph>
                    </div>
                  ),
                };
              })}
            />
          </div>
        ) : (
          <Typography.Text>Нет данных</Typography.Text>
        )}
      </Modal>
    </div>
  );
};

