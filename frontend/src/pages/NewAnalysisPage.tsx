import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Steps, Card, Checkbox, Table, Input, Space, message, Typography } from "antd";
import type { CheckboxChangeEvent } from "antd/es/checkbox";
import { api } from "../api/client";
import type { Call } from "../api/client";

const { TextArea } = Input;
const { Title } = Typography;

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

  useEffect(() => {
    loadCalls();
  }, []);

  const loadCalls = async () => {
    try {
      const data = await api.getCalls();
      setCalls(data.map((call) => ({ ...call, checked: false })));
    } catch (error) {
      message.error("Ошибка загрузки звонков");
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

  const handleCreateAnalysis = async () => {
    if (!queryText.trim()) {
      message.error("Введите текст запроса");
      return;
    }
    if (selectedCallIds.length === 0) {
      message.error("Выберите хотя бы один звонок");
      return;
    }

    setLoading(true);
    try {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'NewAnalysisPage.tsx:60','message':'handleCreateAnalysis start','data':{selectedCallIds,queryTextLength:queryText.length,analysisName},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      const analysis = await api.createAnalysis({
        name: analysisName || `Исследование ${new Date().toLocaleString()}`,
        query_text: queryText,
        call_ids: selectedCallIds,
      });
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'NewAnalysisPage.tsx:67','message':'analysis created','data':{analysisId:analysis.id,analysisStatus:analysis.status},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      message.success("Исследование создано и запущено");
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'NewAnalysisPage.tsx:70','message':'navigating with navigate hook','data':{targetUrl:`/analysis/${analysis.id}/status`},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      navigate(`/analysis/${analysis.id}/status`);
    } catch (error: any) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/6f31bf09-72db-41f8-9544-249c90b36fae',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'NewAnalysisPage.tsx:73','message':'handleCreateAnalysis error','data':{error:error?.response?.data?.detail||error?.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      message.error(error.response?.data?.detail || "Ошибка создания исследования");
    } finally {
      setLoading(false);
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
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: "Статус",
      dataIndex: "status",
      key: "status",
    },
  ];

  const steps = [
    {
      title: "Выбор звонков",
      content: (
        <Card>
          <Space direction="vertical" style={{ width: "100%" }} size="large">
            <div>
              Выбрано звонков: <strong>{selectedCallIds.length}</strong>
            </div>
            <Table
              columns={columns}
              dataSource={calls}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Space>
        </Card>
      ),
    },
    {
      title: "Формулирование запроса",
      content: (
        <Card>
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <div>
              <Title level={5}>Название исследования (необязательно)</Title>
              <Input
                value={analysisName}
                onChange={(e) => setAnalysisName(e.target.value)}
                placeholder="Например: Анализ причин отказов"
              />
            </div>
            <div>
              <Title level={5}>Исследовательский запрос</Title>
              <TextArea
                rows={8}
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                placeholder='Например: "Для каждого звонка определи:
1. Была ли покупка совершена? (Да/Нет)
2. Если нет, какая конкретная причина отказа?
3. Упоминались ли конкуренты? Если да, какие?"
'
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
            disabled={selectedCallIds.length === 0 || !queryText.trim()}
          >
            Запустить анализ
          </Button>
        )}
      </Space>
    </div>
  );
};

