import React, { useState, useEffect } from 'react'
import { Button, message, Progress, Input, Card, Typography, Space, Spin, Alert, Select } from 'antd'
import { CloudDownloadOutlined, InfoCircleOutlined, LinkOutlined, FileTextOutlined } from '@ant-design/icons'
import { projectApi, VideoCategory } from '../services/api'

const { Text, Title } = Typography
const { Option } = Select

interface RemoteVideoDownloadProps {
  onDownloadSuccess?: (projectId: string) => void
}

interface RemoteDownloadTask {
  task_id: string
  video_url: string
  subtitle_url?: string
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'error'
  progress: number
  status_message: string
  project_id?: string
  error?: string
  created_at: string
  updated_at: string
}

const RemoteVideoDownload: React.FC<RemoteVideoDownloadProps> = ({ onDownloadSuccess }) => {
  const [videoUrl, setVideoUrl] = useState('')
  const [subtitleUrl, setSubtitleUrl] = useState('')
  const [projectName, setProjectName] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [subtitleMode, setSubtitleMode] = useState<string>('auto')  // 新增字幕模式状态
  const [categories, setCategories] = useState<VideoCategory[]>([])
  const [loadingCategories, setLoadingCategories] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [currentTask, setCurrentTask] = useState<RemoteDownloadTask | null>(null)
  const [pollingInterval, setPollingInterval] = useState<number | null>(null)
  const [error, setError] = useState('')

  // 加载视频分类配置
  useEffect(() => {
    const loadCategories = async () => {
      setLoadingCategories(true)
      try {
        const response = await projectApi.getVideoCategories()
        setCategories(response.categories)
        if (response.default_category) {
          setSelectedCategory(response.default_category)
        } else if (response.categories.length > 0) {
          setSelectedCategory(response.categories[0].value)
        }
      } catch (error) {
        console.error('Failed to load video categories:', error)
        message.error('加载视频分类失败')
      } finally {
        setLoadingCategories(false)
      }
    }

    loadCategories()
  }, [])

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [pollingInterval])

  const validateUrl = (url: string): boolean => {
    try {
      new URL(url)
      return true
    } catch {
      return false
    }
  }

  const resetForm = () => {
    setVideoUrl('')
    setSubtitleUrl('')
    setProjectName('')
    setSubtitleMode('auto')
    setCurrentTask(null)
    setError('')
    if (categories.length > 0) {
      setSelectedCategory(categories[0].value)
    }
  }

  const startPolling = (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const task = await fetch(`/api/remote-download/tasks/${taskId}`).then(res => res.json())
        setCurrentTask(task)
        
        if (task.status === 'completed') {
          clearInterval(interval)
          setPollingInterval(null)
          setDownloading(false)
          message.success('远程视频下载完成，项目创建成功！')
          
          if (task.project_id && onDownloadSuccess) {
            onDownloadSuccess(task.project_id)
          }
          
          // 重置状态
          resetForm()
        } else if (task.status === 'error') {
          clearInterval(interval)
          setPollingInterval(null)
          setDownloading(false)
          message.error(`下载失败: ${task.error || '未知错误'}`)
        }
      } catch (error: unknown) {
        console.error('轮询任务状态失败:', error)
      }
    }, 2000)
    
    setPollingInterval(interval)
  }

  const handleDownload = async () => {
    if (!videoUrl.trim()) {
      message.error('请输入视频URL')
      return
    }

    if (!validateUrl(videoUrl.trim())) {
      message.error('请输入有效的视频URL')
      return
    }

    if (subtitleUrl && !validateUrl(subtitleUrl.trim())) {
      message.error('请输入有效的字幕URL')
      return
    }

    if (!projectName.trim()) {
      message.error('请输入项目名称')
      return
    }

    setDownloading(true)
    setError('')
    
    try {
      const requestBody = {
        video_url: videoUrl.trim(),
        subtitle_url: subtitleUrl.trim() || undefined,
        project_name: projectName.trim(),
        video_category: selectedCategory,
        subtitle_mode: subtitleMode
      }

      const response = await fetch('/api/remote-download/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error('创建下载任务失败')
      }

      const result = await response.json()
      message.success('下载任务创建成功，正在处理...')
      
      setCurrentTask({
        task_id: result.task_id,
        video_url: videoUrl.trim(),
        subtitle_url: subtitleUrl.trim() || undefined,
        status: 'pending',
        progress: 0,
        status_message: '等待开始下载',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
      
      // 开始轮询任务状态
      startPolling(result.task_id)
      
    } catch (error) {
      message.error('创建下载任务失败，请重试')
      console.error('Remote download error:', error)
      setDownloading(false)
    }
  }

  return (
    <Card 
      title={
        <Space>
          <CloudDownloadOutlined style={{ color: '#4facfe' }} />
          <span>远程视频下载</span>
        </Space>
      }
      style={{ marginBottom: '24px' }}
    >
      {/* URL输入区域 */}
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 视频URL */}
        <div>
          <Text strong style={{ marginBottom: '8px', display: 'block' }}>
            <LinkOutlined /> 视频URL *
          </Text>
          <Input
            placeholder="请输入您服务器上的视频文件URL，如: https://yourserver.com/video.mp4"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            disabled={downloading}
            size="large"
          />
        </div>

        {/* 字幕URL */}
        <div>
          <Text strong style={{ marginBottom: '8px', display: 'block' }}>
            <FileTextOutlined /> 字幕URL (可选)
          </Text>
          <Input
            placeholder="请输入字幕文件URL，如: https://yourserver.com/subtitle.srt"
            value={subtitleUrl}
            onChange={(e) => setSubtitleUrl(e.target.value)}
            disabled={downloading}
            size="large"
          />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            🤖 如果不提供字幕URL，系统将使用AI语音识别（Whisper）自动生成字幕
          </Text>
        </div>

        {/* 项目名称 */}
        <div>
          <Text strong style={{ marginBottom: '8px', display: 'block' }}>
            项目名称 *
          </Text>
          <Input
            placeholder="为您的项目起个名字"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            disabled={downloading}
            size="large"
          />
        </div>

        {/* 视频分类 */}
        <div>
          <Text strong style={{ marginBottom: '8px', display: 'block' }}>
            视频分类
          </Text>
          <Select
            value={selectedCategory}
            onChange={setSelectedCategory}
            disabled={downloading || loadingCategories}
            style={{ width: '100%' }}
            size="large"
            loading={loadingCategories}
          >
            {categories.map((category) => (
              <Option key={category.value} value={category.value}>
                {category.label}
              </Option>
            ))}
          </Select>
        </div>

        {/* 字幕模式 */}
        <div>
          <Text strong style={{ marginBottom: '8px', display: 'block' }}>
            字幕处理模式
          </Text>
          <Select
            value={subtitleMode}
            onChange={setSubtitleMode}
            disabled={downloading}
            style={{ width: '100%' }}
            size="large"
          >
            <Option value="auto">
              🤖 智能模式（推荐）- 优先提取内嵌字幕，失败后使用语音识别
            </Option>
            <Option value="extract">
              📄 仅提取 - 只从视频提取内嵌字幕
            </Option>
            <Option value="generate">
              🎤 仅生成 - 只使用语音识别生成字幕
            </Option>
          </Select>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            📝 建议使用智能模式，系统会自动选择最优的字幕获取方式
          </Text>
        </div>

        {/* 错误提示 */}
        {error && (
          <Alert message={error} type="error" showIcon />
        )}

        {/* 下载进度 */}
        {downloading && currentTask && (
          <div>
            <Text strong style={{ marginBottom: '8px', display: 'block' }}>
              下载进度
            </Text>
            <Progress 
              percent={Math.round(currentTask.progress)} 
              status={currentTask.status === 'error' ? 'exception' : 'active'}
              strokeColor={{
                '0%': '#4facfe',
                '100%': '#00f2fe',
              }}
            />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {currentTask.status_message}
            </Text>
          </div>
        )}

        {/* 下载按钮 */}
        <Button
          type="primary"
          icon={<CloudDownloadOutlined />}
          onClick={handleDownload}
          loading={downloading}
          disabled={!videoUrl.trim() || !projectName.trim() || downloading}
          size="large"
          block
          style={{
            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            border: 'none',
            height: '48px',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          {downloading ? '下载中...' : '开始下载'}
        </Button>
      </Space>

      {/* 说明信息 */}
      <Alert
        message="远程视频下载说明"
        description={
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            <li>确保视频URL可以直接访问下载</li>
            <li>支持的视频格式：MP4、AVI、MOV、MKV、WebM</li>
            <li>字幕文件格式：SRT</li>
            <li>🤖 <strong>智能字幕处理</strong>：</li>
            <ul style={{ marginTop: '4px' }}>
              <li>智能模式：自动检测并提取视频内嵌字幕，失败后使用Whisper语音识别</li>
              <li>仅提取模式：只从视频提取已有的内嵌字幕</li>
              <li>仅生成模式：使用OpenAI Whisper语音识别生成字幕</li>
            </ul>
            <li>下载完成后会自动进入AI处理流程</li>
          </ul>
        }
        type="info"
        showIcon
        style={{ marginTop: '16px' }}
      />
    </Card>
  )
}

export default RemoteVideoDownload