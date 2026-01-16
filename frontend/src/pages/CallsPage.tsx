import React from "react";
import { Button, Table, Upload, message, Tag, Space } from "antd";
import type { UploadProps } from "antd";
import { UploadOutlined, DeleteOutlined } from "@ant-design/icons";
import { api, Call } from "../api/client";

export const CallsPage: React.FC = () => {
  const [calls, setCalls] = React.useState<Call[]>([]);
  const [loading, setLoading] = React.useState(false);

  const loadCalls = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getCalls();
      setCalls(data);
    } catch (e) {
      message.error("Не удалось загрузить список звонков");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadCalls();
  }, [loadCalls]);

  const uploadProps: UploadProps = {
    name: "files",
    multiple: true,
    showUploadList: false,
    customRequest: async (options) => {
      const { file, onError, onSuccess } = options;
      try {
        await api.uploadCalls([file as File]);
        message.success("Файлы загружены");
        void loadCalls();
        onSuccess?.({}, new XMLHttpRequest());
      } catch (err) {
        message.error("Ошибка при загрузке файлов");
        onError?.(err as Error);
      }
    },
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteCall(id);
      message.success("Звонок удалён");
      void loadCalls();
    } catch {
      message.error("Не удалось удалить звонок");
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />}>Загрузить звонки (MP3/WAV)</Button>
        </Upload>
        <Button onClick={() => loadCalls()}>Обновить</Button>
      </Space>

      <Table<Call>
        rowKey="id"
        dataSource={calls}
        loading={loading}
        columns={[
          { title: "ID", dataIndex: "id", width: 80 },
          { title: "Файл", dataIndex: "filename" },
          {
            title: "Статус",
            dataIndex: "status",
            width: 120,
            render: (value: string) => {
              let color = "default";
              if (value === "new") color = "blue";
              else if (value === "processed") color = "green";
              else if (value === "error") color = "red";
              else if (value === "processing") color = "gold";
              return <Tag color={color}>{value}</Tag>;
            },
          },
          {
            title: "",
            key: "actions",
            width: 80,
            render: (_, record) => (
              <Button
                type="text"
                icon={<DeleteOutlined />}
                danger
                onClick={() => handleDelete(record.id)}
              />
            ),
          },
        ]}
      />
    </div>
  );
};


