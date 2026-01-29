import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Steps,
  Card,
  Checkbox,
  Table,
  Input,
  Space,
  message,
  Typography,
  Select,
  Tag,
  Divider,
  Radio,
} from "antd";
import type { CheckboxChangeEvent } from "antd/es/checkbox";
import {
  RocketOutlined,
  FileTextOutlined,
  ExperimentOutlined,
  SafetyOutlined,
} from "@ant-design/icons";
import { api, AnalysisTemplate } from "../api/client";
import type { Call } from "../api/client";

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

interface CallWithChecked extends Call {
  checked?: boolean;
}

export const NewAnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [calls, setCalls] = useState<CallWithChecked[]>([]);
  const [selectedCallIds, setSelectedCallIds] = useState<number[]>([]);
  const [queryText, setQueryText] = useState("");
  const [analysisName, setAnalysisName] = useState("");
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<AnalysisTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [useTemplate, setUseTemplate] = useState<"template" | "custom">("template");

  useEffect(() => {
    loadCalls();
    loadTemplates();
  }, []);

  const loadCalls = async () => {
    try {
      const data = await api.getCalls();
      setCalls(data.map((call) => ({ ...call, checked: false })));
    } catch (error) {
      message.error("Ошибка загрузки звонков");
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates();
      setTemplates(data);
      // Выбираем шаблон агрессии по умолчанию если есть
      const aggressionTemplate = data.find((t) => t.name.includes("агрессии") || t.name.includes("Агрессии"));
      if (aggressionTemplate) {
        setSelectedTemplateId(aggressionTemplate.id);
      } else if (data.length > 0) {
        setSelectedTemplateId(data[0].id);
      }
    } catch (error) {
      console.error("Ошибка загрузки шаблонов");
    }
  };

  const onSelectAll = (e: CheckboxChangeEvent) => {
    const checked = e.target.checked;
    setCalls(calls.map((c) => ({ ...c, checked })));
    setSelectedCallIds(checked ? calls.map((c) => c.id) : []);
  };

  const onSelectOne = (callId: number, checked: boolean) => {
    setCalls(calls.map((c) => (c.id === callId ? { ...c, checked } : c)));
    if (checked) {
      setSelectedCallIds([...selectedCallIds, callId]);
    } else {
      setSelectedCallIds(selectedCallIds.filter((id) => id !== callId));
    }
  };

  const getSelectedTemplate = () => {
    return templates.find((t) => t.id === selectedTemplateId);
  };

  const handleCreateAnalysis = async () => {
    const finalQueryText = useTemplate === "template"
      ? getSelectedTemplate()?.query_text || ""
      : queryText;

    if (!finalQueryText.trim()) {
      message.error("Выберите шаблон или введите текст запроса");
      return;
    }
    if (selectedCallIds.length === 0) {
      message.error("Выберите хотя бы один звонок");
      return;
    }

    const finalName = analysisName ||
      (useTemplate === "template" && getSelectedTemplate()
        ? `${getSelectedTemplate()?.name} - ${new Date().toLocaleDateString("ru-RU")}`
        : `Исследование ${new Date().toLocaleString()}`);

    setLoading(true);
    try {
      const analysis = await api.createAnalysis({
        name: finalName,
        query_text: finalQueryText,
        call_ids: selectedCallIds,
      });
      message.success("Исследование создано и запущено");
      navigate(`/analysis/${analysis.id}/status`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || "Ошибка создания исследования");
    } finally {
      setLoading(false);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "security":
        return <SafetyOutlined style={{ color: "#f5222d" }} />;
      case "quality":
        return <ExperimentOutlined style={{ color: "#1890ff" }} />;
      case "sales":
        return <RocketOutlined style={{ color: "#52c41a" }} />;
      default:
        return <FileTextOutlined />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case "security":
        return "Безопасность";
      case "quality":
        return "Качество";
      case "sales":
        return "Продажи";
      default:
        return "Общее";
    }
  };

  const columns = [
    {
      title: (
        <Checkbox
          checked={calls.length > 0 && calls.every((c) => c.checked)}
          indeterminate={
            calls.some((c) => c.checked) && !calls.every((c) => c.checked)
          }
          onChange={onSelectAll}
        />
      ),
      key: "checkbox",
      width: 50,
      render: (_: any, record: CallWithChecked) => (
        <Checkbox
          checked={record.checked}
          onChange={(e) => onSelectOne(record.id, e.target.checked)}
        />
      ),
    },
    {
      title: "Название файла",
      dataIndex: "filename",
      key: "filename",
    },
    {
      title: "Дата загрузки",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (text: string) => new Date(text).toLocaleString("ru-RU"),
    },
    {
      title: "Статус",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (value: string) => {
        let color = "default";
        let label = value;
        if (value === "new") { color = "blue"; label = "Новый"; }
        else if (value === "processed") { color = "green"; label = "Обработан"; }
        else if (value === "error") { color = "red"; label = "Ошибка"; }
        return <Tag color={color}>{label}</Tag>;
      },
    },
  ];

  const steps = [
    {
      title: "Выбор файлов",
      content: (
        <Card>
          <Space direction="vertical" style={{ width: "100%" }} size="large">
            <div>
              <Text strong>Выбрано файлов: </Text>
              <Tag color="blue">{selectedCallIds.length}</Tag>
              {selectedCallIds.length > 0 && (
                <Button type="link" onClick={() => {
                  setCalls(calls.map((c) => ({ ...c, checked: false })));
                  setSelectedCallIds([]);
                }}>
                  Сбросить
                </Button>
              )}
            </div>
            <Table
              columns={columns}
              dataSource={calls}
              rowKey="id"
              pagination={{ pageSize: 10, showSizeChanger: true }}
              size="small"
            />
          </Space>
        </Card>
      ),
    },
    {
      title: "Тип анализа",
      content: (
        <Card>
          <Space direction="vertical" style={{ width: "100%" }} size="large">
            <div>
              <Title level={5}>Выберите способ анализа</Title>
              <Radio.Group
                value={useTemplate}
                onChange={(e) => setUseTemplate(e.target.value)}
                style={{ marginBottom: 16 }}
              >
                <Radio.Button value="template">Использовать шаблон</Radio.Button>
                <Radio.Button value="custom">Свой запрос</Radio.Button>
              </Radio.Group>
            </div>

            {useTemplate === "template" ? (
              <div>
                <Title level={5}>Выберите шаблон анализа</Title>
                <Select
                  style={{ width: "100%" }}
                  value={selectedTemplateId}
                  onChange={setSelectedTemplateId}
                  size="large"
                >
                  {templates.map((template) => (
                    <Select.Option key={template.id} value={template.id}>
                      <Space>
                        {getCategoryIcon(template.category)}
                        <span>{template.name}</span>
                        {template.is_system && <Tag color="blue">Системный</Tag>}
                      </Space>
                    </Select.Option>
                  ))}
                </Select>

                {getSelectedTemplate() && (
                  <Card
                    size="small"
                    style={{ marginTop: 16, background: "#f6ffed", borderColor: "#b7eb8f" }}
                  >
                    <Space direction="vertical" style={{ width: "100%" }}>
                      <div>
                        <Tag color="green">{getCategoryLabel(getSelectedTemplate()!.category)}</Tag>
                        <Text strong style={{ marginLeft: 8 }}>{getSelectedTemplate()!.name}</Text>
                      </div>
                      {getSelectedTemplate()!.description && (
                        <Text type="secondary">{getSelectedTemplate()!.description}</Text>
                      )}
                      <Divider style={{ margin: "8px 0" }} />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Превью запроса:
                      </Text>
                      <Paragraph
                        ellipsis={{ rows: 4, expandable: true }}
                        style={{ background: "#fff", padding: 8, borderRadius: 4, marginBottom: 0 }}
                      >
                        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
                          {getSelectedTemplate()!.query_text}
                        </pre>
                      </Paragraph>
                    </Space>
                  </Card>
                )}
              </div>
            ) : (
              <div>
                <Title level={5}>Исследовательский запрос</Title>
                <TextArea
                  rows={10}
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder={`Опишите что нужно найти в записях. Например:

"Для каждой записи определи:
1. Есть ли признаки агрессии? (Да/Нет)
2. Если да, укажи тайм-коды и описание
3. Какой уровень серьёзности?"`}
                />
              </div>
            )}

            <div>
              <Title level={5}>Название исследования (необязательно)</Title>
              <Input
                value={analysisName}
                onChange={(e) => setAnalysisName(e.target.value)}
                placeholder="Например: Анализ агрессии - Январь 2025"
              />
            </div>
          </Space>
        </Card>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Создание нового исследования</Title>
      <Steps current={currentStep} style={{ marginBottom: 24 }}>
        {steps.map((step, idx) => (
          <Steps.Step key={idx} title={step.title} />
        ))}
      </Steps>

      <div style={{ marginBottom: 24 }}>{steps[currentStep].content}</div>

      <Space>
        {currentStep > 0 && (
          <Button onClick={() => setCurrentStep(currentStep - 1)}>Назад</Button>
        )}
        {currentStep < steps.length - 1 ? (
          <Button
            type="primary"
            onClick={() => setCurrentStep(currentStep + 1)}
            disabled={selectedCallIds.length === 0}
          >
            Далее
          </Button>
        ) : (
          <Button
            type="primary"
            onClick={handleCreateAnalysis}
            loading={loading}
            disabled={
              selectedCallIds.length === 0 ||
              (useTemplate === "template" && !selectedTemplateId) ||
              (useTemplate === "custom" && !queryText.trim())
            }
          >
            Запустить анализ ({selectedCallIds.length} файлов)
          </Button>
        )}
      </Space>
    </div>
  );
};
