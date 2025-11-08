import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Play, Pause, Scissors, RotateCcw, Download, Share2, ArrowLeft, ZoomIn, ZoomOut } from 'lucide-react';

function VideoEditor() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30);
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(30);
  const [zoom, setZoom] = useState(1);
  const videoRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      
      if (videoRef.current.currentTime >= trimEnd) {
        videoRef.current.pause();
        videoRef.current.currentTime = trimStart;
        setIsPlaying(false);
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      const videoDuration = videoRef.current.duration;
      setDuration(videoDuration);
      setTrimEnd(Math.min(30, videoDuration));
    }
  };

  const handleSeek = (e) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
  };

  const handleReset = () => {
    setTrimStart(0);
    setTrimEnd(duration);
    setCurrentTime(0);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
    }
  };

  return (
    <div className="video-editor-container">
      <div className="editor-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={20} />
          Back to Dashboard
        </button>
        <h1>Video Editor</h1>
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

      <div className="editor-workspace">
        <div className="video-preview">
          <div className="preview-container" style={{ transform: `scale(${zoom})` }}>
            <video
              ref={videoRef}
              className="video-player"
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              src="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>
          
          <div className="zoom-controls">
            <button onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}>
              <ZoomOut size={16} />
            </button>
            <span>{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom(Math.min(2, zoom + 0.25))}>
              <ZoomIn size={16} />
            </button>
          </div>

          <div className="playback-controls">
            <button className="control-btn" onClick={handlePlayPause}>
              {isPlaying ? <Pause size={24} /> : <Play size={24} />}
            </button>
            <span className="time-display">{formatTime(currentTime)} / {formatTime(trimEnd - trimStart)}</span>
            <button className="control-btn" onClick={handleReset}>
              <RotateCcw size={20} />
            </button>
          </div>
        </div>

        <div className="editor-panel">
          <div className="timeline-section">
            <h3>Timeline</h3>
            <div className="timeline">
              <input
                type="range"
                min="0"
                max={duration}
                step="0.1"
                value={currentTime}
                onChange={handleSeek}
                className="timeline-slider"
              />
              <div className="timeline-markers">
                <span>{formatTime(0)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>
          </div>

          <div className="trim-section">
            <h3>
              <Scissors size={18} />
              Trim Controls
            </h3>
            <div className="trim-controls">
              <div className="trim-input">
                <label>Start Time</label>
                <input
                  type="number"
                  min="0"
                  max={trimEnd - 1}
                  value={trimStart}
                  onChange={(e) => setTrimStart(Math.min(parseFloat(e.target.value), trimEnd - 1))}
                  step="0.1"
                />
                <span>{formatTime(trimStart)}</span>
              </div>
              <div className="trim-input">
                <label>End Time</label>
                <input
                  type="number"
                  min={trimStart + 1}
                  max={duration}
                  value={trimEnd}
                  onChange={(e) => setTrimEnd(Math.max(parseFloat(e.target.value), trimStart + 1))}
                  step="0.1"
                />
                <span>{formatTime(trimEnd)}</span>
              </div>
            </div>
            <div className="duration-display">
              Duration: {formatTime(trimEnd - trimStart)}
            </div>
          </div>

          <div className="effects-section">
            <h3>Effects & Enhancements</h3>
            <div className="effects-grid">
              <button className="effect-btn">Add Captions</button>
              <button className="effect-btn">Voice Dubbing</button>
              <button className="effect-btn">Add Music</button>
              <button className="effect-btn">Apply Filters</button>
            </div>
          </div>

          <div className="export-settings">
            <h3>Export Settings</h3>
            <div className="settings-group">
              <label>Platform</label>
              <select className="platform-select">
                <option>YouTube Shorts</option>
                <option>Instagram Reels</option>
                <option>TikTok</option>
                <option>Facebook</option>
                <option>LinkedIn</option>
              </select>
            </div>
            <div className="settings-group">
              <label>Quality</label>
              <select className="quality-select">
                <option>1080p (Best)</option>
                <option>720p (Good)</option>
                <option>480p (Fast)</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VideoEditor;
