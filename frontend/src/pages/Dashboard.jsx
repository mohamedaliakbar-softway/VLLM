import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Video, Play, Trash2, Download, Calendar, TrendingUp, ArrowLeft, 
  BarChart3, Eye, Plus, Sparkles, Film
} from 'lucide-react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

function Dashboard() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState(null);
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

  const handleDownload = async (video) => {
    setDownloadingId(video.id);
    
    try {
      // Construct download URL - adjust based on your API
      const downloadUrl = video.download_url || `/api/v1/download/${video.filename || video.id}`;
      
      // Fetch the video file
      const response = await axios.get(downloadUrl, {
        responseType: 'blob'
      });

      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: 'video/mp4' });
      const url = globalThis.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${video.title.replaceAll(/[^a-z0-9]/gi, '_').toLowerCase()}.mp4`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      globalThis.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Download error:', error);
      globalThis.alert('Failed to download video. Please try again.');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleTimelineFilter = (filter) => {
    setTimelineFilter(filter);
    // Here you would filter videos based on the timeline
    // For now, we'll just update the state
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Enhanced Header */}
      <div className="border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Button variant="ghost" onClick={() => navigate('/')}>
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            </div>
            <div className="flex items-center gap-3">
              <Sparkles className="h-6 w-6 text-[#1E201E]" />
              <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
            </div>
            <div>
              <Button className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white" onClick={() => navigate('/')}>
                <Plus className="h-4 w-4" />
                Create New
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Welcome Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome back!</h2>
            <p className="text-gray-600">Manage your AI-generated video shorts and track performance</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => navigate('/')}>
              <Film className="h-4 w-4" />
              New Project
            </Button>
            <Button variant="outline" onClick={() => navigate('/editor')}>
              <BarChart3 className="h-4 w-4" />
              Analytics
            </Button>
          </div>
        </div>

        {/* Enhanced Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-[#1E201E] rounded-lg flex items-center justify-center">
                  <Video className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Total Videos</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.totalVideos}</p>
                  <p className="text-xs text-green-600 font-semibold">+2 this week</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center">
                  <Film className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Generated Shorts</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.totalShorts}</p>
                  <p className="text-xs text-green-600 font-semibold">+5 this week</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
                  <Eye className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Total Views</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.totalViews.toLocaleString()}</p>
                  <p className="text-xs text-green-600 font-semibold">+12% this week</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Avg Engagement</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.avgEngagement}%</p>
                  <p className="text-xs text-green-600 font-semibold">+3.2% this week</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Videos Section with Timeline Filter */}
        <div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Your Videos</h2>
            <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
              {['all', 'week', 'month', 'year'].map((filter) => (
                <Button
                  key={filter}
                  variant={timelineFilter === filter ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => handleTimelineFilter(filter)}
                  className={timelineFilter === filter ? 'bg-[#1E201E] hover:bg-[#1E201E]/90 text-white' : ''}
                >
                  {filter === 'all' ? 'All Time' : filter === 'week' ? 'This Week' : filter === 'month' ? 'This Month' : 'This Year'}
                </Button>
              ))}
            </div>
          </div>
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#1E201E]"></div>
              <p className="mt-4 text-gray-600">Loading your videos...</p>
            </div>
          ) : videos.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <Video className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-4">No videos yet</p>
                <Button className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white" onClick={() => navigate('/')}>
                  Create Your First Short
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {videos.map((video) => (
                <Card key={video.id} className="overflow-hidden hover:shadow-lg transition-shadow">
                  <div className="relative aspect-video bg-gray-100 overflow-hidden">
                    <img src={video.thumbnail} alt={video.title} className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center">
                      <Button size="icon" className="rounded-full bg-white/90 hover:bg-white text-[#1E201E]">
                        <Play className="h-6 w-6" />
                      </Button>
                    </div>
                  </div>
                  <CardHeader>
                    <CardTitle className="text-lg">{video.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {new Date(video.createdAt).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <Play className="h-4 w-4" />
                        {video.shorts} shorts
                      </span>
                    </div>
                    <div className="flex gap-6 py-4 border-t border-b border-gray-200 mb-4">
                      <div>
                        <p className="text-xs text-gray-600">Views</p>
                        <p className="text-lg font-semibold text-gray-900">{video.views}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600">Engagement</p>
                        <p className="text-lg font-semibold text-gray-900">{video.engagement}%</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => navigate('/editor', { state: { videoId: video.id } })}
                      >
                        <Play className="h-4 w-4" />
                        Edit
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => handleDownload(video)}
                        disabled={downloadingId === video.id}
                      >
                        <Download className="h-4 w-4" />
                        {downloadingId === video.id ? '...' : 'Download'}
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleDelete(video.id)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
