import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Play, Pause, Download, Share2, ArrowLeft,
  MessageSquare, Send, Plus, ChevronUp, ChevronDown, SkipForward, SkipBackIcon,
  Loader2
} from 'lucide-react';
import axios from 'axios';
import { extractVideoId, getThumbnailUrl } from '../utils/youtube';

function VideoEditor() {
  const navigate = useNavigate();
  const location = useLocation();
  const videoRef = useRef(null);
  
  const youtubeUrl = location.state?.youtubeUrl;
  const videoId = extractVideoId(youtubeUrl);
  const thumbnailUrl = getThumbnailUrl(videoId);

  // Processing states
  const [isProcessing, setIsProcessing] = useState(true);
  const [processingStatus, setProcessingStatus] = useState('Analyzing video...');
  const [error, setError] = useState('');
  const [shorts, setShorts] = useState([]);

  // Video playback states
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30);
  const [selectedClipIndex, setSelectedClipIndex] = useState(0);
  
  // Chat states
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: 'Hello! I\'m analyzing your video and will generate highlights shortly.' }
  ]);

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
        const { status, shorts: generatedShorts, progress } = response.data;

        if (progress) {
          setProcessingStatus(progress);
        }

        if (status === 'completed' && generatedShorts && generatedShorts.length > 0) {
          clearInterval(poll);
          setShorts(generatedShorts);
          
          // Convert shorts to clips format
          const newClips = generatedShorts.map((short, idx) => ({
            id: idx + 1,
            title: short.title || `Highlight ${idx + 1}`,
            startTime: formatTime(short.start_time),
            endTime: formatTime(short.end_time),
            duration: short.duration || 30,
            filename: short.filename,
            url: `/api/v1/download/${short.filename}`
          }));
          
          setClips(newClips);
          setIsProcessing(false);
          setChatHistory(prev => [...prev, { 
            role: 'assistant', 
            content: `✅ Generated ${generatedShorts.length} video highlights! Click any clip to preview.` 
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
      }
    }, 1000);

    return poll; // Return interval ID for cleanup
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
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
    }
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    setChatHistory([...chatHistory, { role: 'user', content: chatMessage }]);
    setChatMessage('');

    setTimeout(() => {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: 'I can help you with that! What would you like to do with this clip?' 
      }]);
    }, 1000);
  };

  const handleQuickAction = (action) => {
    setChatHistory([...chatHistory, { role: 'user', content: action }]);
    setTimeout(() => {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `Processing: ${action}` 
      }]);
    }, 1000);
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
          <button className="action-btn" disabled={isProcessing}>
            <Download size={18} />
            Export
          </button>
          <button className="action-btn primary" disabled={isProcessing}>
            <Share2 size={18} />
            Publish
          </button>
        </div>
      </div>

      <div className="editor-workspace-new">
        {/* Left Panel - Assistant Chat */}
        <aside className="assistant-panel">
          <div className="panel-header">
            <MessageSquare size={20} />
            <div>
              <h3>Assistant</h3>
              <p>Chat with Gemini</p>
            </div>
          </div>

          <div className="quick-actions">
            <button className="quick-action-btn" onClick={() => handleQuickAction('Use example video')}>
              Use example video
            </button>
            <button className="quick-action-btn" onClick={() => handleQuickAction('Add live captions')}>
              Add live captions
            </button>
            <button className="quick-action-btn" onClick={() => handleQuickAction('Dub in Kannada')}>
              Dub in Kannada
            </button>
            <button className="quick-action-btn" onClick={() => handleQuickAction('Summarize scenes')}>
              Summarize scenes
            </button>
            <button className="quick-action-btn" onClick={() => handleQuickAction('Change video URL')}>
              Change video URL
            </button>
          </div>

          <div className="chat-history">
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role}`}>
                <p>{msg.content}</p>
              </div>
            ))}
          </div>

          <form className="chat-input-form" onSubmit={handleSendMessage}>
            <input
              type="text"
              placeholder="Ask me anything..."
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              className="chat-input"
              disabled={isProcessing}
            />
            <button type="submit" className="chat-send-btn" disabled={isProcessing}>
              <Send size={18} />
            </button>
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
                  <Loader2 size={64} className="spinner-icon" />
                  <p className="loading-text">{processingStatus}</p>
                  <div className="loading-bar">
                    <div className="loading-bar-fill"></div>
                  </div>
                </div>
              </div>
            ) : clips.length > 0 && selectedClip?.url ? (
              // Show video player when ready
              <>
                <video
                  ref={videoRef}
                  className="video-player-new"
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  src={selectedClip.url}
                  key={selectedClip.url}
                />
                <div className="video-overlay">
                  <button className="play-overlay-btn" onClick={handlePlayPause}>
                    {isPlaying ? <Pause size={48} /> : <Play size={48} />}
                  </button>
                </div>
                <div className="clip-label">Clip #{selectedClipIndex + 1}</div>
              </>
            ) : (
              <div className="preview-error">
                <p>{error || 'No video available'}</p>
              </div>
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

            <div className="clips-timeline">
              {isProcessing ? (
                <div className="timeline-loading">
                  <p>Generating clips...</p>
                </div>
              ) : clips.length > 0 ? (
                clips.map((clip, idx) => (
                  <div
                    key={clip.id}
                    className={`clip-item ${idx === selectedClipIndex ? 'selected' : ''}`}
                    onClick={() => setSelectedClipIndex(idx)}
                  >
                    <div className="clip-name">{clip.title}</div>
                  </div>
                ))
              ) : (
                <div className="timeline-empty">
                  <p>No clips yet</p>
                </div>
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
                <label>Title</label>
                <input
                  type="text"
                  value={clipTitle}
                  onChange={(e) => setClipTitle(e.target.value)}
                  className="property-input"
                  disabled={isProcessing}
                />
              </div>

              <div className="property-group">
                <label>Time Range</label>
                <div className="time-range-inputs">
                  <input
                    type="text"
                    value={selectedClip.startTime}
                    readOnly
                    className="time-input"
                  />
                  <input
                    type="text"
                    value={selectedClip.endTime}
                    readOnly
                    className="time-input"
                  />
                </div>
              </div>

              <div className="property-group">
                <label>Duration</label>
                <div className="duration-slider">
                  <input
                    type="range"
                    min="15"
                    max="60"
                    value={clipDuration}
                    onChange={(e) => setClipDuration(parseInt(e.target.value))}
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

              <div className="property-group">
                <label>Trim</label>
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

              <div className="property-group">
                <label>Order</label>
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
    </div>
  );
}

export default VideoEditor;
