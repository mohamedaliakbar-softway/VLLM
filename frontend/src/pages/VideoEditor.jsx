import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Play, Pause, SkipBack, Download, Share2, ArrowLeft,
  MessageSquare, Send, Plus, ChevronUp, ChevronDown, SkipForward, SkipBackIcon
} from 'lucide-react';

function VideoEditor() {
  const navigate = useNavigate();
  const location = useLocation();
  const videoRef = useRef(null);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30);
  const [selectedClipIndex, setSelectedClipIndex] = useState(0);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'assistant', content: 'You are a helpful editor assistant.' }
  ]);

  // Mock clips data (will be replaced with actual data from backend)
  const [clips, setClips] = useState([
    { id: 1, title: 'Epic Highlight Moment', startTime: '00:02:34', endTime: '00:02:58', duration: 24 },
    { id: 2, title: 'Key Action Sequence', startTime: '00:05:12', endTime: '00:05:42', duration: 30 },
    { id: 3, title: 'Emotional Peak', startTime: '00:08:45', endTime: '00:09:00', duration: 15 },
    { id: 4, title: 'Grand Finale', startTime: '00:12:20', endTime: '00:12:50', duration: 30 }
  ]);

  const selectedClip = clips[selectedClipIndex];
  const [clipTitle, setClipTitle] = useState(selectedClip.title);
  const [clipDuration, setClipDuration] = useState(selectedClip.duration);

  // Sync properties panel with selected clip when selection changes
  useEffect(() => {
    if (selectedClip) {
      setClipTitle(selectedClip.title);
      setClipDuration(selectedClip.duration);
    }
  }, [selectedClipIndex]);

  // Update clip in array when title or duration changes
  useEffect(() => {
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
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={20} />
          Back
        </button>
        <h2 className="editor-title">Video Editor</h2>
        <div className="editor-actions">
          <button className="action-btn">
            <Download size={18} />
            Export
          </button>
          <button className="action-btn primary">
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
              placeholder="Analyze this video: tuefn"
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              className="chat-input"
            />
            <button type="submit" className="chat-send-btn">
              <Send size={18} />
            </button>
          </form>
        </aside>

        {/* Center Panel - Video Preview */}
        <main className="preview-panel">
          <div className="video-container">
            <video
              ref={videoRef}
              className="video-player-new"
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            />
            <div className="video-overlay">
              <button className="play-overlay-btn" onClick={handlePlayPause}>
                {isPlaying ? <Pause size={48} /> : <Play size={48} />}
              </button>
            </div>
            <div className="clip-label">Clip #{selectedClipIndex + 1}</div>
          </div>

          {/* Timeline Section */}
          <div className="timeline-section">
            <div className="timeline-header">
              <h4>Timeline</h4>
              <div className="timeline-controls">
                <button className="timeline-btn" onClick={addClip}>
                  <Plus size={16} />
                  Add Clip
                </button>
                <button className="timeline-btn" onClick={() => moveClip(-1)} disabled={selectedClipIndex === 0}>
                  <ChevronUp size={16} />
                  Move Up
                </button>
                <button className="timeline-btn" onClick={() => moveClip(1)} disabled={selectedClipIndex === clips.length - 1}>
                  <ChevronDown size={16} />
                  Move Down
                </button>
              </div>
            </div>

            <div className="clips-timeline">
              {clips.map((clip, idx) => (
                <div
                  key={clip.id}
                  className={`clip-item ${idx === selectedClipIndex ? 'selected' : ''}`}
                  onClick={() => setSelectedClipIndex(idx)}
                >
                  <div className="clip-name">{clip.title}</div>
                </div>
              ))}
            </div>
          </div>
        </main>

        {/* Right Panel - Properties */}
        <aside className="properties-panel">
          <div className="panel-header">
            <h3>Properties</h3>
            <p>Edit selected clip</p>
          </div>

          <div className="properties-content">
            <div className="property-group">
              <label>Title</label>
              <input
                type="text"
                value={clipTitle}
                onChange={(e) => setClipTitle(e.target.value)}
                className="property-input"
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
                />
                <span className="duration-value">{clipDuration}s</span>
              </div>
              <div className="duration-presets">
                <button 
                  className={clipDuration === 15 ? 'active' : ''}
                  onClick={() => setClipDuration(15)}
                >
                  15s
                </button>
                <button 
                  className={clipDuration === 30 ? 'active' : ''}
                  onClick={() => setClipDuration(30)}
                >
                  30s
                </button>
                <button 
                  className={clipDuration === 60 ? 'active' : ''}
                  onClick={() => setClipDuration(60)}
                >
                  60s
                </button>
              </div>
            </div>

            <div className="property-group">
              <label>Trim</label>
              <div className="trim-controls">
                <button className="trim-btn">
                  <SkipBackIcon size={16} />
                  Trim Start
                </button>
                <button className="trim-btn">
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
        </aside>
      </div>
    </div>
  );
}

export default VideoEditor;
