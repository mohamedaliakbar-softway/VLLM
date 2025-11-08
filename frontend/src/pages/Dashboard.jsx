import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Video, Play, Trash2, Download, Calendar, TrendingUp, ArrowLeft, 
  BarChart3, Eye, Plus, Sparkles, Film
} from 'lucide-react';

function Dashboard() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timelineFilter, setTimelineFilter] = useState('all');
  const [stats, setStats] = useState({
    totalVideos: 0,
    totalShorts: 0,
    totalViews: 0,
    avgEngagement: 0
  });
  const navigate = useNavigate();

  useEffect(() => {
    // Mock data for demonstration
    setTimeout(() => {
      setVideos([
        {
          id: 1,
          title: 'Marketing Tips for Beginners',
          thumbnail: 'https://via.placeholder.com/300x200',
          createdAt: '2024-01-15',
          shorts: 3,
          views: 1500,
          engagement: 87
        },
        {
          id: 2,
          title: 'Product Launch Strategy',
          thumbnail: 'https://via.placeholder.com/300x200',
          createdAt: '2024-01-14',
          shorts: 2,
          views: 890,
          engagement: 92
        },
      ]);
      setStats({
        totalVideos: 2,
        totalShorts: 5,
        totalViews: 2390,
        avgEngagement: 89.5
      });
      setLoading(false);
    }, 500);
  }, []);

  const handleDelete = async (videoId) => {
    if (globalThis.confirm('Are you sure you want to delete this video and all its shorts?')) {
      setVideos(videos.filter(v => v.id !== videoId));
    }
  };

  const handleTimelineFilter = (filter) => {
    setTimelineFilter(filter);
    // Here you would filter videos based on the timeline
    // For now, we'll just update the state
  };

  return (
    <div className="dashboard-container">
      {/* Enhanced Header */}
      <div className="dashboard-nav">
        <div className="nav-left">
          <button className="back-btn" onClick={() => navigate('/')}>
            <ArrowLeft size={20} />
            Back
          </button>
        </div>
        <div className="nav-center">
          <div className="dashboard-logo">
            <Sparkles size={24} />
            <h1>Dashboard</h1>
          </div>
        </div>
        <div className="nav-right">
          <button className="create-new-btn" onClick={() => navigate('/')}>
            <Plus size={20} />
            Create New
          </button>
        </div>
      </div>

      {/* Welcome Section */}
      <div className="dashboard-welcome">
        <div className="welcome-content">
          <h2>Welcome back!</h2>
          <p>Manage your AI-generated video shorts and track performance</p>
        </div>
        <div className="welcome-actions">
          <button className="quick-action-dashboard" onClick={() => navigate('/')}>
            <Film size={18} />
            New Project
          </button>
          <button className="quick-action-dashboard" onClick={() => navigate('/editor')}>
            <BarChart3 size={18} />
            Analytics
          </button>
        </div>
      </div>

      {/* Enhanced Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon video-icon">
            <Video size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Videos</p>
            <p className="stat-value">{stats.totalVideos}</p>
            <p className="stat-change positive">+2 this week</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon shorts-icon">
            <Film size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Generated Shorts</p>
            <p className="stat-value">{stats.totalShorts}</p>
            <p className="stat-change positive">+5 this week</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon views-icon">
            <Eye size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Views</p>
            <p className="stat-value">{stats.totalViews.toLocaleString()}</p>
            <p className="stat-change positive">+12% this week</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon engagement-icon">
            <TrendingUp size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Avg Engagement</p>
            <p className="stat-value">{stats.avgEngagement}%</p>
            <p className="stat-change positive">+3.2% this week</p>
          </div>
        </div>
      </div>

      {/* Videos Section with Timeline Filter */}
      <div className="videos-section">
        <div className="section-header">
          <h2>Your Videos</h2>
          <div className="timeline-filter">
            <button 
              className={`timeline-btn-dashboard ${timelineFilter === 'all' ? 'active' : ''}`}
              onClick={() => handleTimelineFilter('all')}
            >
              All Time
            </button>
            <button 
              className={`timeline-btn-dashboard ${timelineFilter === 'week' ? 'active' : ''}`}
              onClick={() => handleTimelineFilter('week')}
            >
              This Week
            </button>
            <button 
              className={`timeline-btn-dashboard ${timelineFilter === 'month' ? 'active' : ''}`}
              onClick={() => handleTimelineFilter('month')}
            >
              This Month
            </button>
            <button 
              className={`timeline-btn-dashboard ${timelineFilter === 'year' ? 'active' : ''}`}
              onClick={() => handleTimelineFilter('year')}
            >
              This Year
            </button>
          </div>
        </div>
        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading your videos...</p>
          </div>
        ) : videos.length === 0 ? (
          <div className="empty-state">
            <Video size={64} />
            <p>No videos yet</p>
            <button onClick={() => navigate('/')} className="create-btn">
              Create Your First Short
            </button>
          </div>
        ) : (
          <div className="videos-grid">
            {videos.map((video) => (
              <div key={video.id} className="video-card">
                <div className="video-thumbnail">
                  <img src={video.thumbnail} alt={video.title} />
                  <div className="video-overlay">
                    <button className="play-btn">
                      <Play size={32} />
                    </button>
                  </div>
                </div>
                <div className="video-info">
                  <h3>{video.title}</h3>
                  <div className="video-meta">
                    <span>
                      <Calendar size={14} />
                      {new Date(video.createdAt).toLocaleDateString()}
                    </span>
                    <span>
                      <Play size={14} />
                      {video.shorts} shorts
                    </span>
                  </div>
                  <div className="video-stats">
                    <div className="stat">
                      <span className="stat-label">Views</span>
                      <span className="stat-value">{video.views}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Engagement</span>
                      <span className="stat-value">{video.engagement}%</span>
                    </div>
                  </div>
                  <div className="video-actions">
                    <button className="action-btn" onClick={() => navigate('/video-editor', { state: { videoId: video.id } })}>
                      <Play size={16} />
                      Edit
                    </button>
                    <button className="action-btn">
                      <Download size={16} />
                      Download
                    </button>
                    <button className="action-btn danger" onClick={() => handleDelete(video.id)}>
                      <Trash2 size={16} />
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
