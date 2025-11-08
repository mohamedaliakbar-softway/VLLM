import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Sparkles, ArrowRight, Upload, Link2, FileVideo, LayoutDashboard } from 'lucide-react';
import axios from 'axios';

function Landing() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploadMethod, setUploadMethod] = useState('url'); // 'url' or 'file'
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post('/api/v1/generate-shorts', {
        youtube_url: youtubeUrl,
        max_shorts: 3,
      });

      const jobId = response.data.job_id;
      
      navigate('/editor', { state: { jobId, youtubeUrl } });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process video. Please try again.');
      setLoading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    // Try multiple data transfer formats
    let droppedText = e.dataTransfer.getData('text/uri-list') || 
                     e.dataTransfer.getData('text/plain') || 
                     e.dataTransfer.getData('text');
    
    // Clean up the URL (remove whitespace and newlines)
    droppedText = droppedText.trim().split('\n')[0];
    
    if (droppedText && (droppedText.includes('youtube.com') || droppedText.includes('youtu.be') || droppedText.includes('whatsapp.com'))) {
      setYoutubeUrl(droppedText);
    }
  };

  return (
    <div className="landing-container">
      <div className="landing-content">
        <button
          className="dashboard-nav-btn"
          onClick={() => navigate('/dashboard')}
        >
          <LayoutDashboard size={20} />
          My Dashboard
        </button>

        <div className="hero-section">
          <div className="logo">
            <Video size={48} />
          </div>
          <h1>
            <Sparkles className="sparkle-icon" />
            AI-Powered Video Shorts Generator
          </h1>
          <p className="subtitle">
            Transform long-form YouTube videos into engaging 15-30 second shorts
            with AI-powered analysis and editing
          </p>
        </div>

        <div className="upload-method-toggle">
          <button
            className={`toggle-btn ${uploadMethod === 'url' ? 'active' : ''}`}
            onClick={() => setUploadMethod('url')}
          >
            <Link2 size={18} />
            Paste Link
          </button>
          <button
            className={`toggle-btn ${uploadMethod === 'file' ? 'active' : ''}`}
            onClick={() => setUploadMethod('file')}
          >
            <Upload size={18} />
            Drag & Drop
          </button>
        </div>

        {uploadMethod === 'url' ? (
          <form onSubmit={handleSubmit} className="url-form">
            <div className="input-group">
              <input
                type="url"
                placeholder="Enter YouTube or WhatsApp video link (15-30 min)"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                required
                disabled={loading}
                className="url-input"
              />
              <button type="submit" disabled={loading || !youtubeUrl} className="generate-btn">
                {loading ? (
                  <>
                    <div className="spinner"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    Generate Shorts
                    <ArrowRight size={20} />
                  </>
                )}
              </button>
            </div>
            {error && <div className="error-message">{error}</div>}
          </form>
        ) : (
          <div
            className={`drop-zone ${isDragging ? 'dragging' : ''} ${youtubeUrl ? 'has-link' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <FileVideo size={48} className="drop-icon" />
            {youtubeUrl ? (
              <>
                <p className="drop-text success">Link detected! Click below to generate shorts</p>
                <p className="drop-url">{youtubeUrl}</p>
                <button onClick={handleSubmit} disabled={loading} className="generate-btn">
                  {loading ? (
                    <>
                      <div className="spinner"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      Generate Shorts
                      <ArrowRight size={20} />
                    </>
                  )}
                </button>
              </>
            ) : (
              <>
                <p className="drop-text">Drag and drop your YouTube or WhatsApp link here</p>
                <p className="drop-hint">or paste it in the box above</p>
              </>
            )}
          </div>
        )}

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>AI Analysis</h3>
            <p>Gemini AI identifies the most engaging segments</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">✂️</div>
            <h3>Smart Clipping</h3>
            <p>Automatically creates optimized shorts</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3>AI Chat Editing</h3>
            <p>Edit shorts with natural conversation</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🚀</div>
            <h3>One-Click Publish</h3>
            <p>Share to all platforms instantly</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
