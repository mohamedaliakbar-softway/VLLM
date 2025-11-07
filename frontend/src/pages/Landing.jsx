import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Sparkles, ArrowRight } from 'lucide-react';
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

      navigate('/editor', { state: { jobData: response.data } });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process video. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="landing-container">
      <div className="landing-content">
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

        <form onSubmit={handleSubmit} className="url-form">
          <div className="input-group">
            <input
              type="url"
              placeholder="Enter YouTube URL (15-30 min video)"
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
