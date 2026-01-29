import React, { useCallback, useRef } from "react";
import { Button, Table, Upload, message, Tag, Space, Progress, Card, Typography, Statistic, Row, Col } from "antd";
import type { UploadProps } from "antd";
import { UploadOutlined, DeleteOutlined, FolderOpenOutlined, InboxOutlined } from "@ant-design/icons";
import { api, Call } from "../api/client";

const { Title, Text } = Typography;

export const CallsPage: React.FC = () => {
  const [calls, setCalls] = React.useState<Call[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [uploadProgress, setUploadProgress] = React.useState({ current: 0, total: 0, filename: "" });
  const [pendingFiles, setPendingFiles] = React.useState<File[]>([]);
  const [isDragging, setIsDragging] = React.useState(false);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const loadCalls = useCallback(async () => {
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

  // Пакетная загрузка файлов
  const uploadBatch = async (files: File[]) => {
    if (files.length === 0) return;

    setUploading(true);
    setUploadProgress({ current: 0, total: files.length, filename: "" });

    let successCount = 0;
    let errorCount = 0;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setUploadProgress({ current: i + 1, total: files.length, filename: file.name });

      try {
        await api.uploadCalls([file]);
        successCount++;
      } catch {
        errorCount++;
        console.error(`Ошибка загрузки: ${file.name}`);
      }
    }

    setUploading(false);
    setPendingFiles([]);

    if (errorCount === 0) {
      message.success(`Успешно загружено ${successCount} файлов`);
    } else {
      message.warning(`Загружено: ${successCount}, ошибок: ${errorCount}`);
    }

    void loadCalls();
  };

  // Рекурсивное чтение директории через File System Access API
  const readDirectory = async (entry: FileSystemDirectoryEntry): Promise<File[]> => {
    const files: File[] = [];
    const reader = entry.createReader();

    const readEntries = (): Promise<FileSystemEntry[]> => {
      return new Promise((resolve, reject) => {
        reader.readEntries(resolve, reject);
      });
    };

    const getFile = (fileEntry: FileSystemFileEntry): Promise<File> => {
      return new Promise((resolve, reject) => {
        fileEntry.file(resolve, reject);
      });
    };

    let entries = await readEntries();
    while (entries.length > 0) {
      for (const entry of entries) {
        if (entry.isFile) {
          const file = await getFile(entry as FileSystemFileEntry);
          const name = file.name.toLowerCase();
          if (name.endsWith(".wav") || name.endsWith(".mp3")) {
            files.push(file);
          }
        } else if (entry.isDirectory) {
          const subFiles = await readDirectory(entry as FileSystemDirectoryEntry);
          files.push(...subFiles);
        }
      }
      entries = await readEntries();
    }

    return files;
  };

  // Обработка drag & drop
  const handleDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const items = e.dataTransfer.items;
    const allFiles: File[] = [];

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const entry = item.webkitGetAsEntry();

      if (entry) {
        if (entry.isDirectory) {
          // Это папка - читаем рекурсивно
          const files = await readDirectory(entry as FileSystemDirectoryEntry);
          allFiles.push(...files);
        } else if (entry.isFile) {
          // Это файл
          const file = item.getAsFile();
          if (file) {
            const name = file.name.toLowerCase();
            if (name.endsWith(".wav") || name.endsWith(".mp3")) {
              allFiles.push(file);
            }
          }
        }
      }
    }

    if (allFiles.length > 0) {
      setPendingFiles(allFiles);
      message.info(`Найдено ${allFiles.length} аудиофайлов`);
    } else {
      message.warning("WAV или MP3 файлы не найдены");
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  // Стандартная загрузка файлов через кнопку
  const uploadProps: UploadProps = {
    name: "files",
    multiple: true,
    showUploadList: false,
    accept: ".mp3,.wav",
    beforeUpload: (file, fileList) => {
      const validFiles = fileList.filter(
        (f) => f.name.toLowerCase().endsWith(".wav") || f.name.toLowerCase().endsWith(".mp3")
      );
      if (validFiles.length > 0) {
        setPendingFiles(validFiles);
      }
      return false;
    },
  };

  // Выбор папки через input с webkitdirectory
  const folderInputRef = useRef<HTMLInputElement>(null);

  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    const validFiles: File[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const name = file.name.toLowerCase();
      if (name.endsWith(".wav") || name.endsWith(".mp3")) {
        validFiles.push(file);
      }
    }

    if (validFiles.length > 0) {
      setPendingFiles(validFiles);
      message.info(`Найдено ${validFiles.length} аудиофайлов`);
    } else {
      message.warning("WAV или MP3 файлы не найдены в папке");
    }

    // Сбрасываем input чтобы можно было выбрать ту же папку снова
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
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

  // Статистика по статусам
  const stats = React.useMemo(() => {
    const newCount = calls.filter((c) => c.status === "new").length;
    const processedCount = calls.filter((c) => c.status === "processed").length;
    const errorCount = calls.filter((c) => c.status === "error").length;
    return { total: calls.length, new: newCount, processed: processedCount, error: errorCount };
  }, [calls]);

  return (
    <div>
      <Title level={2}>Управление аудиофайлами</Title>

      {/* Статистика */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="Всего файлов" value={stats.total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Новые" value={stats.new} valueStyle={{ color: "#1890ff" }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Обработаны" value={stats.processed} valueStyle={{ color: "#52c41a" }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="С ошибками" value={stats.error} valueStyle={{ color: "#ff4d4f" }} />
          </Card>
        </Col>
      </Row>

      {/* Drag & Drop зона */}
      <Card style={{ marginBottom: 24 }}>
        <div
          ref={dropZoneRef}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          style={{
            border: `2px dashed ${isDragging ? "#1890ff" : "#d9d9d9"}`,
            borderRadius: 8,
            padding: "40px 20px",
            textAlign: "center",
            background: isDragging ? "#e6f7ff" : "#fafafa",
            transition: "all 0.3s",
            cursor: "pointer",
          }}
        >
          <InboxOutlined style={{ fontSize: 48, color: isDragging ? "#1890ff" : "#999" }} />
          <p style={{ fontSize: 16, margin: "16px 0 8px", color: isDragging ? "#1890ff" : "#666" }}>
            {isDragging ? "Отпустите для загрузки" : "Перетащите папку или файлы сюда"}
          </p>
          <p style={{ color: "#999", margin: 0 }}>
            Поддерживаются форматы WAV и MP3
          </p>
        </div>

        <Space style={{ marginTop: 16 }}>
          {/* Скрытый input для выбора папки */}
          <input
            ref={folderInputRef}
            type="file"
            // @ts-ignore - webkitdirectory не типизирован в React
            webkitdirectory=""
            directory=""
            multiple
            style={{ display: "none" }}
            onChange={handleFolderSelect}
          />
          <Button
            icon={<FolderOpenOutlined />}
            onClick={() => folderInputRef.current?.click()}
          >
            Выбрать папку
          </Button>
          <Upload {...uploadProps}>
            <Button icon={<UploadOutlined />}>Выбрать файлы</Button>
          </Upload>
          <Button onClick={() => loadCalls()} disabled={uploading}>
            Обновить список
          </Button>
        </Space>

        {/* Список выбранных файлов для загрузки */}
        {pendingFiles.length > 0 && !uploading && (
          <Card size="small" style={{ marginTop: 16, background: "#f6ffed", borderColor: "#b7eb8f" }}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Text strong>Выбрано файлов: {pendingFiles.length}</Text>
              <Text type="secondary">
                {pendingFiles.slice(0, 5).map((f) => f.name).join(", ")}
                {pendingFiles.length > 5 && ` и ещё ${pendingFiles.length - 5}...`}
              </Text>
              <Space>
                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  onClick={() => uploadBatch(pendingFiles)}
                >
                  Загрузить {pendingFiles.length} файлов
                </Button>
                <Button onClick={() => setPendingFiles([])}>Отмена</Button>
              </Space>
            </Space>
          </Card>
        )}

        {/* Прогресс загрузки */}
        {uploading && (
          <Card size="small" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: "100%" }}>
              <Text strong>
                Загрузка: {uploadProgress.current} / {uploadProgress.total}
              </Text>
              <Text type="secondary">{uploadProgress.filename}</Text>
              <Progress
                percent={Math.round((uploadProgress.current / uploadProgress.total) * 100)}
                status="active"
              />
            </Space>
          </Card>
        )}
      </Card>

      {/* Таблица файлов */}
      <Table<Call>
        rowKey="id"
        dataSource={calls}
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `Всего: ${total}` }}
        columns={[
          { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
          {
            title: "Файл",
            dataIndex: "filename",
            sorter: (a, b) => a.filename.localeCompare(b.filename),
          },
          {
            title: "Размер",
            dataIndex: "size_bytes",
            width: 120,
            render: (value: number | null) => {
              if (!value) return "-";
              if (value < 1024) return `${value} B`;
              if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
              return `${(value / 1024 / 1024).toFixed(1)} MB`;
            },
            sorter: (a, b) => (a.size_bytes || 0) - (b.size_bytes || 0),
          },
          {
            title: "Статус",
            dataIndex: "status",
            width: 120,
            filters: [
              { text: "Новый", value: "new" },
              { text: "Обработан", value: "processed" },
              { text: "Ошибка", value: "error" },
              { text: "В обработке", value: "processing" },
            ],
            onFilter: (value, record) => record.status === value,
            render: (value: string) => {
              let color = "default";
              let label = value;
              if (value === "new") { color = "blue"; label = "Новый"; }
              else if (value === "processed") { color = "green"; label = "Обработан"; }
              else if (value === "error") { color = "red"; label = "Ошибка"; }
              else if (value === "processing") { color = "gold"; label = "В обработке"; }
              return <Tag color={color}>{label}</Tag>;
            },
          },
          {
            title: "Дата загрузки",
            dataIndex: "created_at",
            width: 180,
            render: (value: string) => new Date(value).toLocaleString("ru-RU"),
            sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
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
