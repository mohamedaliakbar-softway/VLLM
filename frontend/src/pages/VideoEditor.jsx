import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Play, Pause, Download, Share2, ArrowLeft,
  Send, Plus, ChevronUp, ChevronDown, SkipForward, SkipBackIcon,
  Loader2, Scissors, Type, Volume2, Wand2, Layers, Copy, Trash2, 
  ZoomIn, ZoomOut, RotateCw, Maximize2, Save, Sparkles, Video,
  GripVertical, Maximize, Minimize
} from 'lucide-react';
import axios from 'axios';
import { extractVideoId, getThumbnailUrl } from '../utils/youtube';

function VideoEditor() {
  const navigate = useNavigate();
  const location = useLocation();
  const videoRef = useRef(null);
  const hasProcessedRef = useRef(false); // Track if video has been processed to prevent double submission
  
  const youtubeUrl = location.state?.youtubeUrl;
  const videoId = extractVideoId(youtubeUrl);
  const thumbnailUrl = getThumbnailUrl(videoId);

  // Processing states
  const [isProcessing, setIsProcessing] = useState(true);
  const [processingStatus, setProcessingStatus] = useState('Analyzing video...');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [error, setError] = useState('');

  // Video playback states
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [selectedClipIndex, setSelectedClipIndex] = useState(0);
  
  // Publish modal states
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [publishSettings, setPublishSettings] = useState({
    title: '',
    description: '',
    tags: '',
    aspectRatio: '9:16' // Default for shorts
  });
  
  // Chat states
  const [chatMessage, setChatMessage] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    { 
      role: 'assistant', 
      content: 'Hello! I\'m your AI video editor assistant. I can help you trim clips, adjust duration, add effects, and more. Just tell me what you want to do!',
      timestamp: new Date().toISOString()
    }
  ]);

  // Resizable chat panel states
  const [chatPanelWidth, setChatPanelWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);

  // Clips data
  const [clips, setClips] = useState([]);
  const selectedClip = clips[selectedClipIndex];
  const [clipTitle, setClipTitle] = useState(selectedClip?.title || '');
  const [clipDuration, setClipDuration] = useState(selectedClip?.duration || 30);

  // Redirect if no YouTube URL
  useEffect(() => {
    if (!youtubeUrl) {
      navigate('/');
    }
  }, [youtubeUrl, navigate]);

  // Trigger video processing on mount
  useEffect(() => {
    if (!youtubeUrl) return;
    
    // Prevent double submission (React StrictMode runs effects twice in dev)
    if (hasProcessedRef.current) return;
    hasProcessedRef.current = true;

    let pollInterval = null;

    const processVideo = async () => {
      try {
        setProcessingStatus('Extracting transcript...');
        
        const response = await axios.post('/api/v1/generate-shorts', {
          youtube_url: youtubeUrl,
          max_shorts: 3,
        });

        setProcessingStatus('AI analyzing highlights...');
        
        // Poll for results
        const jobId = response.data.job_id;
        pollInterval = pollJobStatus(jobId);
        
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to process video');
        setIsProcessing(false);
        setChatHistory(prev => [...prev, { 
          role: 'assistant', 
          content: `Error: ${err.response?.data?.detail || 'Failed to process video'}` 
        }]);
      }
    };

    processVideo();

    // Cleanup on unmount
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [youtubeUrl]);

  const pollJobStatus = (jobId) => {
    const maxAttempts = 60; // 1 minute timeout
    let attempts = 0;

    const poll = setInterval(async () => {
      try {
        attempts++;
        
        const response = await axios.get(`/api/v1/job/${jobId}`);
        const { status, shorts: generatedShorts, progress, percent } = response.data;

        if (progress) {
          setProcessingStatus(progress);
        }

        // Update progress percentage (0-100)
        if (typeof percent === 'number') {
          setProcessingProgress(Math.min(Math.max(percent, 0), 100));
        } else {
          // Estimate based on attempts if backend doesn't provide
          setProcessingProgress(Math.min((attempts / maxAttempts) * 100, 95));
        }

        if (status === 'completed' && generatedShorts && generatedShorts.length > 0) {
          clearInterval(poll);
          setProcessingProgress(100);
          
          // Convert shorts to clips format
          const newClips = generatedShorts.map((short, idx) => ({
            id: idx + 1,
            title: short.title || `Highlight ${idx + 1}`,
            startTime: formatTime(short.start_time),
            endTime: formatTime(short.end_time),
            duration: short.duration || short.duration_seconds || 30,
            filename: short.filename,
            url: short.download_url || `/api/v1/download/${short.filename}`
          }));
          
          setClips(newClips);
          setIsProcessing(false);
          setChatHistory(prev => [...prev, { 
            role: 'assistant', 
            content: `✅ Generated ${generatedShorts.length} video highlights! Click any clip to preview.`,
            timestamp: new Date().toISOString()
          }]);
        } else if (status === 'failed') {
          clearInterval(poll);
          setError('Video processing failed');
          setIsProcessing(false);
        } else if (attempts >= maxAttempts) {
          clearInterval(poll);
          setError('Processing timeout - please try again');
          setIsProcessing(false);
        }
      } catch (err) {
        clearInterval(poll);
        setError('Failed to check processing status');
        setIsProcessing(false);
        console.error('Error polling job status:', err);
      }
    }, 1000);

    return poll; // Return interval ID for cleanup
  };

  const formatTime = (timeInput) => {
    // Handle both timestamp strings (MM:SS or HH:MM:SS) and seconds (number)
    let seconds = 0;
    
    if (typeof timeInput === 'string') {
      // Parse timestamp string (e.g., "00:30" or "01:30:45")
      const parts = timeInput.split(':').map(Number);
      if (parts.length === 2) {
        // MM:SS format
        seconds = parts[0] * 60 + parts[1];
      } else if (parts.length === 3) {
        // HH:MM:SS format
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
    } else if (typeof timeInput === 'number') {
      seconds = timeInput;
    }
    
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `00:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  // Sync properties panel with selected clip
  useEffect(() => {
    if (selectedClip) {
      setClipTitle(selectedClip.title);
      setClipDuration(selectedClip.duration);
    }
  }, [selectedClipIndex, selectedClip]);

  // Update clip in array when title or duration changes
  useEffect(() => {
    if (!selectedClip) return;
    
    const newClips = [...clips];
    if (newClips[selectedClipIndex]) {
      newClips[selectedClipIndex] = {
        ...newClips[selectedClipIndex],
        title: clipTitle,
        duration: clipDuration
      };
      setClips(newClips);
    }
  }, [clipTitle, clipDuration]);

  // Chat panel resize handlers
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      
      const newWidth = e.clientX;
      if (newWidth >= 280 && newWidth <= 600) {
        setChatPanelWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleResizeStart = () => {
    setIsResizing(true);
  };

  const toggleChatExpand = () => {
    if (isChatExpanded) {
      setChatPanelWidth(320); // Reset to default
      setIsChatExpanded(false);
    } else {
      setChatPanelWidth(600); // Expand to max width
      setIsChatExpanded(true);
    }
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play().catch(err => console.log('Autoplay prevented:', err));
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
      videoRef.current.volume = volume;
    }
  };

  const handleProgressClick = (e) => {
    if (videoRef.current) {
      const rect = e.currentTarget.getBoundingClientRect();
      const pos = (e.clientX - rect.left) / rect.width;
      videoRef.current.currentTime = pos * videoRef.current.duration;
    }
  };

  const handleVolumeChange = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setVolume(pos);
    if (videoRef.current) {
      videoRef.current.volume = pos;
    }
    if (pos > 0) setIsMuted(false);
  };

  const toggleMute = () => {
    if (videoRef.current) {
      if (isMuted) {
        videoRef.current.volume = volume;
        setIsMuted(false);
      } else {
        videoRef.current.volume = 0;
        setIsMuted(true);
      }
    }
  };

  const formatTimeDisplay = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim() || isAiThinking) return;

    const userMessage = chatMessage.trim();
    setChatMessage('');

    // Add user message to chat
    setChatHistory(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);

    // Show AI thinking state
    setIsAiThinking(true);
    setChatHistory(prev => [...prev, {
      role: 'assistant',
      content: '🤔 Analyzing your request...',
      timestamp: new Date().toISOString(),
      isThinking: true
    }]);

    try {
      // Send message to Gemini AI agent
      const response = await axios.post('/api/v1/ai-agent/execute', {
        message: userMessage,
        context: {
          clips,
          selectedClipIndex,
          selectedClip,
          videoInfo: {
            youtubeUrl,
            videoId
          }
        }
      });

      const { action, parameters, message: aiMessage, updatedClips } = response.data;

      // Remove thinking message
      setChatHistory(prev => prev.filter(msg => !msg.isThinking));

      // Execute the action based on AI response
      if (action && parameters) {
        await executeAiAction(action, parameters, updatedClips);
      }

      // Add AI response to chat
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: aiMessage || 'Done! Let me know if you need anything else.',
        timestamp: new Date().toISOString()
      }]);

    } catch (error) {
      // Remove thinking message
      setChatHistory(prev => prev.filter(msg => !msg.isThinking));

      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: `❌ Sorry, I encountered an error: ${error.response?.data?.detail || error.message}. Please try again.`,
        timestamp: new Date().toISOString()
      }]);
      console.error('AI Agent error:', error);
    } finally {
      setIsAiThinking(false);
    }
  };

  // Execute AI-determined actions
  const executeAiAction = async (action, parameters, updatedClips) => {
    switch (action) {
      case 'trim_clip':
        if (parameters.clipIndex !== undefined && parameters.startTime !== undefined && parameters.endTime !== undefined) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            startTime: formatTime(parameters.startTime),
            endTime: formatTime(parameters.endTime),
            duration: parameters.endTime - parameters.startTime
          };
          setClips(newClips);
        }
        break;

      case 'update_duration':
        if (parameters.clipIndex !== undefined && parameters.duration !== undefined) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            duration: parameters.duration
          };
          setClips(newClips);
          setClipDuration(parameters.duration);
        }
        break;

      case 'update_title':
        if (parameters.clipIndex !== undefined && parameters.title) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            title: parameters.title
          };
          setClips(newClips);
          setClipTitle(parameters.title);
        }
        break;

      case 'select_clip':
        if (parameters.clipIndex !== undefined && parameters.clipIndex < clips.length) {
          setSelectedClipIndex(parameters.clipIndex);
        }
        break;

      case 'delete_clip':
        if (parameters.clipIndex !== undefined) {
          const newClips = clips.filter((_, idx) => idx !== parameters.clipIndex);
          setClips(newClips);
          setSelectedClipIndex(Math.max(0, parameters.clipIndex - 1));
        }
        break;

      case 'duplicate_clip':
        if (parameters.clipIndex !== undefined) {
          const clipToDuplicate = clips[parameters.clipIndex];
          const newClip = {
            ...clipToDuplicate,
            id: clips.length + 1,
            title: `${clipToDuplicate.title} (Copy)`
          };
          setClips([...clips, newClip]);
        }
        break;

      case 'update_clips':
        if (updatedClips && Array.isArray(updatedClips)) {
          setClips(updatedClips);
        }
        break;

      default:
        console.log('Unknown action:', action);
    }
  };

  const handleQuickAction = async (action) => {
    setChatHistory(prev => [...prev, {
      role: 'user',
      content: action,
      timestamp: new Date().toISOString()
    }]);
    
    // Trigger AI processing for quick actions
    const fakeEvent = { preventDefault: () => {}, target: { value: action } };
    setChatMessage(action);
    await handleSendMessage(fakeEvent);
  };

  const moveClip = (direction) => {
    const newIndex = selectedClipIndex + direction;
    if (newIndex >= 0 && newIndex < clips.length) {
      const newClips = [...clips];
      [newClips[selectedClipIndex], newClips[newIndex]] = [newClips[newIndex], newClips[selectedClipIndex]];
      setClips(newClips);
      setSelectedClipIndex(newIndex);
    }
  };

  const addClip = () => {
    const newClip = {
      id: clips.length + 1,
      title: `New Clip ${clips.length + 1}`,
      startTime: '00:00:00',
      endTime: '00:00:30',
      duration: 30
    };
    setClips([...clips, newClip]);
    setSelectedClipIndex(clips.length);
  };

  const handleExport = async () => {
    if (clips.length === 0) return;
    
    try {
      const clip = clips[selectedClipIndex];
      
      // Show notification
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: '📥 Downloading video...',
        timestamp: new Date().toISOString()
      }]);

      // Get the video URL - use download_url if available, otherwise construct it
      const videoUrl = clip.download_url || `/api/v1/download/${clip.filename}`;
      
      // Fetch the video file
      const response = await axios.get(videoUrl, {
        responseType: 'blob',
        onDownloadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProcessingStatus(`Downloading... ${percentCompleted}%`);
          }
        }
      });

      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: 'video/mp4' });
      const url = globalThis.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = clip.filename || `short_${clip.title || selectedClipIndex + 1}.mp4`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      globalThis.URL.revokeObjectURL(url);

      // Success notification
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `✅ Video "${clip.title}" downloaded successfully!`,
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: '❌ Failed to download video. Please try again.',
        timestamp: new Date().toISOString()
      }]);
      console.error('Download error:', error);
    }
  };

  const handlePublish = () => {
    if (clips.length === 0) return;
    
    // Open publish modal instead of directly navigating
    setShowPublishModal(true);
  };

  const handlePlatformToggle = (platform) => {
    if (selectedPlatforms.includes(platform)) {
      setSelectedPlatforms(selectedPlatforms.filter(p => p !== platform));
    } else {
      setSelectedPlatforms([...selectedPlatforms, platform]);
    }
  };

  const handlePublishConfirm = async () => {
    if (selectedPlatforms.length === 0) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: '⚠️ Please select at least one platform to publish.',
        timestamp: new Date().toISOString()
      }]);
      return;
    }

    setShowPublishModal(false);
    
    // Show publishing notification
    setChatHistory(prev => [...prev, { 
      role: 'assistant', 
      content: `🚀 Publishing to ${selectedPlatforms.join(', ')}...`,
      timestamp: new Date().toISOString()
    }]);
    
    // Simulate publishing
    setTimeout(() => {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `✅ Successfully published to ${selectedPlatforms.join(', ')}! Redirecting to dashboard...`,
        timestamp: new Date().toISOString()
      }]);
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    }, 2000);
  };

  const handleDuplicateClip = () => {
    if (!selectedClip) return;
    
    const newClip = {
      ...selectedClip,
      id: clips.length + 1,
      title: `${selectedClip.title} (Copy)`
    };
    setClips([...clips, newClip]);
    setChatHistory(prev => [...prev, { 
      role: 'assistant', 
      content: '✅ Clip duplicated successfully!' 
    }]);
  };

  const handleDeleteClip = () => {
    if (!selectedClip || clips.length <= 1) return;
    
    const newClips = clips.filter((_, idx) => idx !== selectedClipIndex);
    setClips(newClips);
    setSelectedClipIndex(Math.max(0, selectedClipIndex - 1));
    setChatHistory(prev => [...prev, { 
      role: 'assistant', 
      content: '🗑️ Clip deleted successfully!' 
    }]);
  };

  return (
    <div className="editor-new-container">
      {/* Top Navigation */}
      <div className="editor-nav">
        <button className="back-btn" onClick={() => navigate('/')}>
          <ArrowLeft size={20} />
          Back
        </button>
        <h2 className="editor-title">Video Editor</h2>
        <div className="editor-actions">
          <button className="action-btn" onClick={handleExport} disabled={isProcessing || clips.length === 0}>
            <Download size={18} />
            Export
          </button>
          <button className="action-btn primary" onClick={handlePublish} disabled={isProcessing || clips.length === 0}>
            <Share2 size={18} />
            Publish
          </button>
        </div>
      </div>

      <div className="editor-workspace-new">
        {/* Left Panel - Assistant Chat - Resizable */}
        <aside className="assistant-panel" style={{ width: `${chatPanelWidth}px`, minWidth: '280px', maxWidth: '600px' }}>
          {/* Resize Handle */}
          <button 
            className="resize-handle" 
            onMouseDown={handleResizeStart}
            aria-label="Resize chat panel"
            type="button"
          >
            <GripVertical size={16} />
          </button>

          <div className="copilot-chat-header">
            <div className="chat-header-content">
              <Sparkles size={18} className="sparkle-icon-chat" />
              <div className="chat-header-text">
                <h3>Copilot</h3>
                <span className="chat-status">{isAiThinking ? 'Thinking...' : 'Ready to assist'}</span>
              </div>
            </div>
            <button 
              className="expand-chat-btn" 
              onClick={toggleChatExpand}
              aria-label={isChatExpanded ? 'Minimize chat' : 'Maximize chat'}
            >
              {isChatExpanded ? <Minimize size={16} /> : <Maximize size={16} />}
            </button>
          </div>

          <div className="suggestions-section">
            <p className="suggestions-label">Suggestions</p>
            <div className="suggestions-grid">
              <button className="suggestion-chip" onClick={() => handleQuickAction('Use example video')}>
                <Video size={14} />
                <span>Use example video</span>
              </button>
              <button className="suggestion-chip" onClick={() => handleQuickAction('Add live captions')}>
                <Type size={14} />
                <span>Add live captions</span>
              </button>
              <button className="suggestion-chip" onClick={() => handleQuickAction('Dub in Kannada')}>
                <Volume2 size={14} />
                <span>Dub in Kannada</span>
              </button>
              <button className="suggestion-chip" onClick={() => handleQuickAction('Summarize scenes')}>
                <Wand2 size={14} />
                <span>Summarize scenes</span>
              </button>
              <button className="suggestion-chip" onClick={() => handleQuickAction('Change video URL')}>
                <ArrowLeft size={14} />
                <span>Change video URL</span>
              </button>
            </div>
          </div>

          <div className="copilot-chat-messages">
            {chatHistory.map((msg, idx) => (
              <div key={`msg-${idx}-${msg.content.substring(0, 20)}`} className={`copilot-message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'assistant' ? (
                    <Sparkles size={16} />
                  ) : (
                    <span className="user-avatar">You</span>
                  )}
                </div>
                <div className="message-content-wrapper">
                  <div className="message-header">
                    <span className="message-sender">
                      {msg.role === 'assistant' ? 'Copilot' : 'You'}
                    </span>
                    <span className="message-time">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="message-text">
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <form className="copilot-chat-input-form" onSubmit={handleSendMessage}>
            <div className="input-wrapper-copilot">
              <input
                type="text"
                placeholder={isAiThinking ? "AI is processing..." : "Ask Copilot to edit your video..."}
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                className="copilot-input"
                disabled={isAiThinking}
              />
              <button 
                type="submit" 
                className="copilot-send-btn" 
                disabled={isAiThinking || !chatMessage.trim()}
                aria-label="Send message"
              >
                {isAiThinking ? <Loader2 size={18} className="spinner-icon" /> : <Send size={18} />}
              </button>
            </div>
            <p className="input-hint">💡 Try: "Trim clip to 20s" or "Change title to Marketing Tips"</p>
          </form>
        </aside>

        {/* Center Panel - Video Preview */}
        <main className="preview-panel">
          <div className="video-container">
            {isProcessing ? (
              // Show blurred thumbnail while processing
              <div className="preview-loading">
                {thumbnailUrl && (
                  <img 
                    src={thumbnailUrl} 
                    alt="Video thumbnail" 
                    className="blurred-thumbnail"
                  />
                )}
                <div className="loading-overlay">
                  <div className="loader-wrapper">
                    <div className="loader"></div>
                    <span className="loader-percentage">{Math.round(processingProgress)}%</span>
                  </div>
                  <p className="loading-text">{processingStatus}</p>
                </div>
              </div>
            ) : (
              <>
                {clips.length > 0 && selectedClip?.url ? (
                  // Show video player when ready with 9:16 aspect ratio
                  <div className="video-wrapper">
                    <video
                      ref={videoRef}
                      className="video-player-new"
                      onTimeUpdate={handleTimeUpdate}
                      onLoadedMetadata={handleLoadedMetadata}
                                        onError={(e) => {
                    console.error('Video load error:', e);
                    console.error('Video URL:', selectedClip.url);
                    console.error('Video element error details:', videoRef.current?.error);
                    setError(`Failed to load video: ${videoRef.current?.error?.message || 'Unknown error'}`);
                  }}
                  onCanPlay={() => {
                    console.log('Video can play, URL:', selectedClip.url);
                    setError(''); // Clear any previous errors
                  }}
                      onEnded={() => setIsPlaying(false)}
                      src={selectedClip.url}
                      key={selectedClip.url}
                                    controls={false}
                  preload="metadata"
                    >
                      <track kind="captions" srcLang="en" label="English" />
                    </video>
                    
                    <div className="clip-label">Clip #{selectedClipIndex + 1}</div>
                    
                    {/* Video Controls */}
                    <div className="video-controls">
                      <div 
                        className="video-progress" 
                        onClick={handleProgressClick}
                        role="progressbar"
                        aria-label="Video progress"
                        aria-valuenow={currentTime}
                        aria-valuemin={0}
                        aria-valuemax={duration}
                      >
                        <div 
                          className="video-progress-filled" 
                          style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
                        />
                      </div>
                      
                      <div className="video-control-buttons">
                        <button 
                          className="control-btn primary" 
                          onClick={handlePlayPause}
                          aria-label={isPlaying ? "Pause" : "Play"}
                        >
                          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
                        </button>
                        
                        <button 
                          className="control-btn" 
                          onClick={toggleMute}
                          aria-label={isMuted ? "Unmute" : "Mute"}
                        >
                          {isMuted ? <Volume2 size={18} style={{ opacity: 0.5 }} /> : <Volume2 size={18} />}
                        </button>
                        
                        <div className="volume-control">
                          <div 
                            className="volume-slider" 
                            onClick={handleVolumeChange}
                            role="slider"
                            aria-label="Volume"
                            aria-valuenow={Math.round((isMuted ? 0 : volume) * 100)}
                            aria-valuemin={0}
                            aria-valuemax={100}
                          >
                            <div 
                              className="volume-slider-filled" 
                              style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                            />
                          </div>
                        </div>
                        
                        <span className="video-time">
                          {formatTimeDisplay(currentTime)} / {formatTimeDisplay(duration)}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="preview-error">
                    <p>{error || 'No video available'}</p>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Timeline Section */}
          <div className="timeline-section">
            <div className="timeline-header">
              <h4>Timeline</h4>
              <div className="timeline-controls">
                <button className="timeline-btn" onClick={addClip} disabled={isProcessing}>
                  <Plus size={16} />
                  Add Clip
                </button>
                <button 
                  className="timeline-btn" 
                  onClick={() => moveClip(-1)} 
                  disabled={selectedClipIndex === 0 || isProcessing}
                >
                  <ChevronUp size={16} />
                  Move Up
                </button>
                <button 
                  className="timeline-btn" 
                  onClick={() => moveClip(1)} 
                  disabled={selectedClipIndex === clips.length - 1 || isProcessing}
                >
                  <ChevronDown size={16} />
                  Move Down
                </button>
              </div>
            </div>

            {/* Time Ruler */}
            {!isProcessing && clips.length > 0 && selectedClip && (
              <div className="time-ruler">
                <div className="time-markers">
                  {Array.from({ length: Math.ceil(selectedClip.duration / 5) + 1 }, (_, i) => (
                    <div key={i} className="time-marker">
                      <div className="time-tick"></div>
                      <span className="time-label">{i * 5}s</span>
                    </div>
                  ))}
                </div>
                <div className="playhead" style={{ left: `${(currentTime / selectedClip.duration) * 100}%` }}>
                  <div className="playhead-line"></div>
                  <div className="playhead-handle"></div>
                </div>
              </div>
            )}

            <div className="clips-timeline">
              {isProcessing ? (
                <div className="timeline-loading">
                  <p>Generating clips...</p>
                </div>
              ) : (
                <>
                  {clips.length > 0 ? (
                    clips.map((clip, idx) => (
                      <button
                        key={clip.id}
                        className={`clip-item ${idx === selectedClipIndex ? 'selected' : ''}`}
                        onClick={() => setSelectedClipIndex(idx)}
                        type="button"
                        aria-label={`Select clip ${idx + 1}: ${clip.title}`}
                      >
                        <div className="clip-number">#{idx + 1}</div>
                        <div className="clip-name">{clip.title}</div>
                        <div className="clip-duration">{clip.duration}s</div>
                        <div className="clip-time-range">
                          {clip.startTime} - {clip.endTime}
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="timeline-empty">
                      <p>No clips yet</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </main>

        {/* Right Panel - Properties */}
        <aside className="properties-panel">
          <div className="panel-header">
            <h3>Properties</h3>
            <p>Edit selected clip</p>
          </div>

          {selectedClip ? (
            <div className="properties-content">
              <div className="property-group">
                <h4>Title</h4>
                <input
                  type="text"
                  value={clipTitle}
                  onChange={(e) => setClipTitle(e.target.value)}
                  className="property-input"
                  disabled={isProcessing}
                  aria-label="Clip title"
                />
              </div>

              <div className="property-group">
                <h4>Time Range</h4>
                <div className="time-range-inputs">
                  <input
                    type="text"
                    value={selectedClip.startTime}
                    readOnly
                    className="time-input"
                    aria-label="Start time"
                  />
                  <input
                    type="text"
                    value={selectedClip.endTime}
                    readOnly
                    className="time-input"
                    aria-label="End time"
                  />
                </div>
              </div>

              <div className="property-group">
                <h4>Duration</h4>
                <div className="duration-slider">
                  <input
                    type="range"
                    min="15"
                    max="60"
                    value={clipDuration}
                    onChange={(e) => setClipDuration(Number.parseInt(e.target.value, 10))}
                    className="slider"
                    disabled={isProcessing}
                  />
                  <span className="duration-value">{clipDuration}s</span>
                </div>
                <div className="duration-presets">
                  <button 
                    className={clipDuration === 15 ? 'active' : ''}
                    onClick={() => setClipDuration(15)}
                    disabled={isProcessing}
                  >
                    15s
                  </button>
                  <button 
                    className={clipDuration === 30 ? 'active' : ''}
                    onClick={() => setClipDuration(30)}
                    disabled={isProcessing}
                  >
                    30s
                  </button>
                  <button 
                    className={clipDuration === 60 ? 'active' : ''}
                    onClick={() => setClipDuration(60)}
                    disabled={isProcessing}
                  >
                    60s
                  </button>
                </div>
              </div>

              {/* Editing Tools Section */}
              <div className="property-group">
                <h4>Editing Tools</h4>
                <div className="editing-tools-grid">
                  <button className="tool-btn" disabled={isProcessing} title="Trim Clip">
                    <Scissors size={18} />
                    <span>Trim</span>
                  </button>
                  <button className="tool-btn" disabled={isProcessing} title="Add Text">
                    <Type size={18} />
                    <span>Text</span>
                  </button>
                  <button className="tool-btn" disabled={isProcessing} title="Adjust Audio">
                    <Volume2 size={18} />
                    <span>Audio</span>
                  </button>
                  <button className="tool-btn" disabled={isProcessing} title="Apply Effects">
                    <Wand2 size={18} />
                    <span>Effects</span>
                  </button>
                  <button className="tool-btn" disabled={isProcessing} title="Add Layers">
                    <Layers size={18} />
                    <span>Layers</span>
                  </button>
                  <button className="tool-btn" disabled={isProcessing} title="Rotate Video">
                    <RotateCw size={18} />
                    <span>Rotate</span>
                  </button>
                </div>
              </div>

              {/* Transform Section */}
              <div className="property-group">
                <h4>Transform</h4>
                <div className="transform-controls">
                  <button className="transform-btn" disabled={isProcessing}>
                    <ZoomIn size={16} />
                    Zoom In
                  </button>
                  <button className="transform-btn" disabled={isProcessing}>
                    <ZoomOut size={16} />
                    Zoom Out
                  </button>
                  <button className="transform-btn" disabled={isProcessing}>
                    <Maximize2 size={16} />
                    Fit Screen
                  </button>
                </div>
              </div>

              {/* Clip Actions Section */}
              <div className="property-group">
                <h4>Clip Actions</h4>
                <div className="clip-actions">
                  <button className="action-tool-btn" onClick={handleDuplicateClip} disabled={isProcessing}>
                    <Copy size={16} />
                    Duplicate
                  </button>
                  <button className="action-tool-btn save-btn" disabled={isProcessing}>
                    <Save size={16} />
                    Save
                  </button>
                  <button 
                    className="action-tool-btn delete-btn" 
                    onClick={handleDeleteClip} 
                    disabled={isProcessing || clips.length <= 1}
                  >
                    <Trash2 size={16} />
                    Delete
                  </button>
                </div>
              </div>

              {/* Advanced Trim Controls */}
              <div className="property-group">
                <h4>Trim Controls</h4>
                <div className="trim-controls">
                  <button className="trim-btn" disabled={isProcessing}>
                    <SkipBackIcon size={16} />
                    Trim Start
                  </button>
                  <button className="trim-btn" disabled={isProcessing}>
                    Trim End
                    <SkipForward size={16} />
                  </button>
                </div>
              </div>

              {/* Clip Order */}
              <div className="property-group">
                <h4>Clip Order</h4>
                <div className="order-display">
                  <input
                    type="number"
                    value={selectedClipIndex + 1}
                    readOnly
                    className="order-input"
                  />
                  <span>of {clips.length}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="properties-empty">
              <p>{isProcessing ? 'Processing video...' : 'No clip selected'}</p>
            </div>
          )}
        </aside>
      </div>

      {/* Publish Modal */}
      {showPublishModal && (
        <div className="modal-overlay" onClick={() => setShowPublishModal(false)} role="presentation">
          <div className="publish-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="modal-header">
              <h2>Publish Your Short</h2>
              <button className="modal-close" onClick={() => setShowPublishModal(false)} aria-label="Close modal">
                ×
              </button>
            </div>

            <div className="modal-content">
              {/* Platform Selection */}
              <div className="modal-section">
                <h3>Select Platforms</h3>
                <p className="section-description">Choose where you want to publish your video</p>
                <div className="platforms-grid">
                  <button 
                    className={`platform-card ${selectedPlatforms.includes('youtube') ? 'selected' : ''}`}
                    onClick={() => handlePlatformToggle('youtube')}
                  >
                    <div className="platform-icon youtube">
                      <Play size={24} />
                    </div>
                    <div className="platform-info">
                      <h4>YouTube Shorts</h4>
                      <p>9:16 • 60s max</p>
                    </div>
                    {selectedPlatforms.includes('youtube') && (
                      <div className="selected-badge">✓</div>
                    )}
                  </button>

                  <button 
                    className={`platform-card ${selectedPlatforms.includes('instagram') ? 'selected' : ''}`}
                    onClick={() => handlePlatformToggle('instagram')}
                  >
                    <div className="platform-icon instagram">
                      <Video size={24} />
                    </div>
                    <div className="platform-info">
                      <h4>Instagram Reels</h4>
                      <p>9:16 • 90s max</p>
                    </div>
                    {selectedPlatforms.includes('instagram') && (
                      <div className="selected-badge">✓</div>
                    )}
                  </button>

                  <button 
                    className={`platform-card ${selectedPlatforms.includes('tiktok') ? 'selected' : ''}`}
                    onClick={() => handlePlatformToggle('tiktok')}
                  >
                    <div className="platform-icon tiktok">
                      <Play size={24} />
                    </div>
                    <div className="platform-info">
                      <h4>TikTok</h4>
                      <p>9:16 • 10m max</p>
                    </div>
                    {selectedPlatforms.includes('tiktok') && (
                      <div className="selected-badge">✓</div>
                    )}
                  </button>

                  <button 
                    className={`platform-card ${selectedPlatforms.includes('facebook') ? 'selected' : ''}`}
                    onClick={() => handlePlatformToggle('facebook')}
                  >
                    <div className="platform-icon facebook">
                      <Video size={24} />
                    </div>
                    <div className="platform-info">
                      <h4>Facebook Reels</h4>
                      <p>9:16 • 90s max</p>
                    </div>
                    {selectedPlatforms.includes('facebook') && (
                      <div className="selected-badge">✓</div>
                    )}
                  </button>
                </div>
              </div>

              {/* Video Settings */}
              <div className="modal-section">
                <h3>Video Settings</h3>
                <div className="settings-form">
                  <div className="form-group">
                    <label htmlFor="video-title">Title</label>
                    <input
                      id="video-title"
                      type="text"
                      placeholder="Enter video title..."
                      value={publishSettings.title}
                      onChange={(e) => setPublishSettings({...publishSettings, title: e.target.value})}
                      className="form-input"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="video-description">Description</label>
                    <textarea
                      id="video-description"
                      placeholder="Add a description..."
                      value={publishSettings.description}
                      onChange={(e) => setPublishSettings({...publishSettings, description: e.target.value})}
                      className="form-textarea"
                      rows="3"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="video-tags">Tags (comma separated)</label>
                    <input
                      id="video-tags"
                      type="text"
                      placeholder="trending, viral, shorts..."
                      value={publishSettings.tags}
                      onChange={(e) => setPublishSettings({...publishSettings, tags: e.target.value})}
                      className="form-input"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="aspect-ratio">Aspect Ratio</label>
                    <select
                      id="aspect-ratio"
                      value={publishSettings.aspectRatio}
                      onChange={(e) => setPublishSettings({...publishSettings, aspectRatio: e.target.value})}
                      className="form-select"
                    >
                      <option value="9:16">9:16 (Vertical - Recommended)</option>
                      <option value="1:1">1:1 (Square)</option>
                      <option value="16:9">16:9 (Horizontal)</option>
                      <option value="4:5">4:5 (Instagram Feed)</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="modal-btn cancel" onClick={() => setShowPublishModal(false)}>
                Cancel
              </button>
              <button 
                className="modal-btn publish" 
                onClick={handlePublishConfirm}
                disabled={selectedPlatforms.length === 0}
              >
                <Share2 size={18} />
                Publish to {selectedPlatforms.length > 0 ? `${selectedPlatforms.length} Platform${selectedPlatforms.length > 1 ? 's' : ''}` : 'Platforms'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default VideoEditor;
