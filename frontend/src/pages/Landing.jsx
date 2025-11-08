import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Sparkles, ArrowRight, Zap, Clock, Share2 } from 'lucide-react';
import axios from 'axios';

function Landing() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
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
      
      navigate('/video-editor', { state: { jobId, youtubeUrl } });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process video. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="landing-new-container">
      {/* Navigation Bar */}
      <nav className="nav-bar">
        <div className="nav-content">
          <div className="nav-brand">
            <div className="brand-icon">
              <Video size={24} />
            </div>
            <span className="brand-name">HighlightAI</span>
          </div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
            <a href="#pricing">Pricing</a>
          </div>
          <div className="nav-actions">
            <button className="nav-btn-secondary" onClick={() => navigate('/dashboard')}>
              Sign In
            </button>
            <button className="nav-btn-primary">
              <Sparkles size={18} />
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="hero-new-section">
        <div className="ai-badge">
          <Sparkles size={16} />
          AI-Powered Video Highlights
        </div>
        
        <h1 className="hero-title">
          Transform Videos into
          <span className="gradient-block"></span>
        </h1>

        <p className="hero-subtitle">
          Paste any YouTube URL and let our advanced AI extract the most
          <br />
          engaging moments in seconds. Perfect for creating Shorts, Reels, and TikToks.
        </p>

        {/* URL Input */}
        <form onSubmit={handleSubmit} className="url-input-container">
          <input
            type="url"
            placeholder="https://youtube.com/watch?v=..."
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            required
            disabled={loading}
            className="hero-input"
          />
          <button type="submit" disabled={loading || !youtubeUrl} className="hero-generate-btn">
            {loading ? (
              <>
                <div className="spinner"></div>
                Processing...
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Generate
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        {error && <div className="error-banner">{error}</div>}

        <div className="trial-notice">
          <div className="check-icon">✓</div>
          No credit card required • Free trial available
        </div>

        {/* Feature Highlights */}
        <div className="feature-badges">
          <div className="feature-badge">
            <Zap size={20} className="badge-icon" />
            <span>AI-Powered Detection</span>
          </div>
          <div className="feature-badge">
            <Clock size={20} className="badge-icon" />
            <span>2-Minute Processing</span>
          </div>
          <div className="feature-badge">
            <Share2 size={20} className="badge-icon" />
            <span>Multi-Platform Export</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
