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
  const [expandedVideo, setExpandedVideo] = useState(null);
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
          engagement: 87,
          highlights: [
            { id: 1, title: 'Key Strategy #1', duration: '45s', views: 500, platform: 'TikTok' },
            { id: 2, title: 'Pro Marketing Tip', duration: '30s', views: 650, platform: 'Instagram' },
            { id: 3, title: 'Growth Hacks', duration: '60s', views: 350, platform: 'YouTube Shorts' }
          ],
          status: 'completed',
          processingTime: '1m 23s'
        },
        {
          id: 2,
          title: 'Product Launch Strategy',
          thumbnail: 'https://via.placeholder.com/300x200',
          createdAt: '2024-01-14',
          shorts: 2,
          views: 890,
          engagement: 92,
          highlights: [
            { id: 4, title: 'Launch Day Tips', duration: '50s', views: 450, platform: 'Instagram' },
            { id: 5, title: 'Marketing Funnel', duration: '40s', views: 440, platform: 'TikTok' }
          ],
          status: 'completed',
          processingTime: '1m 10s'
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
              {['all', 'week', 'month', 'year'].map((filter) => {
              let filterLabel = 'All Time';
              if (filter === 'week') filterLabel = 'This Week';
              else if (filter === 'month') filterLabel = 'This Month';
              else if (filter === 'year') filterLabel = 'This Year';
              
              return (
                <Button
                  key={filter}
                  variant={timelineFilter === filter ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => handleTimelineFilter(filter)}
                  className={timelineFilter === filter ? 'bg-[#1E201E] hover:bg-[#1E201E]/90 text-white' : ''}
                >
                  {filterLabel}
                </Button>
              );
            })}
            </div>
          </div>
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#1E201E]"></div>
              <p className="mt-4 text-gray-600">Loading your videos...</p>
            </div>
          ) : (
            videos.length === 0 ? (
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
                <div key={video.id} className="group">
                  {/* Main Video Card with Enhanced Design */}
                  <Card className="overflow-hidden hover:shadow-2xl transition-all duration-300 border-0 bg-gradient-to-br from-white to-gray-50">
                    <div className="relative aspect-video bg-gray-100 overflow-hidden">
                      <img src={video.thumbnail} alt={video.title} className="w-full h-full object-cover" />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-all duration-300">
                        <div className="absolute bottom-4 left-4 right-4">
                          <p className="text-white text-sm font-medium mb-2">{video.processingTime} processing</p>
                          <div className="flex gap-2">
                            <Button size="sm" className="bg-white/20 backdrop-blur-sm border border-white/30 text-white hover:bg-white/30">
                              <Play className="h-3 w-3 mr-1" />
                              Preview
                            </Button>
                          </div>
                        </div>
                      </div>
                      {/* Status Badge */}
                      <div className="absolute top-3 right-3">
                        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700">
                          {video.status}
                        </span>
                      </div>
                    </div>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center justify-between">
                        <span className="line-clamp-1">{video.title}</span>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 -mr-2"
                          onClick={() => setExpandedVideo(expandedVideo === video.id ? null : video.id)}
                        >
                          <svg className={`h-4 w-4 transition-transform ${expandedVideo === video.id ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </Button>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5" />
                          {new Date(video.createdAt).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1 font-medium text-purple-600">
                          <Sparkles className="h-3.5 w-3.5" />
                          {video.shorts} AI shorts
                        </span>
                      </div>
                      
                      {/* Stats with Visual Enhancement */}
                      <div className="grid grid-cols-2 gap-3 py-3 px-3 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg mb-4">
                        <div className="text-center">
                          <div className="flex items-center justify-center gap-1">
                            <Eye className="h-3.5 w-3.5 text-gray-500" />
                            <p className="text-lg font-bold text-gray-900">{video.views.toLocaleString()}</p>
                          </div>
                          <p className="text-xs text-gray-600 mt-0.5">Total Views</p>
                        </div>
                        <div className="text-center">
                          <div className="flex items-center justify-center gap-1">
                            <TrendingUp className="h-3.5 w-3.5 text-green-500" />
                            <p className="text-lg font-bold text-green-600">{video.engagement}%</p>
                          </div>
                          <p className="text-xs text-gray-600 mt-0.5">Engagement</p>
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
                
                {/* Expandable Highlights Section */}
                {expandedVideo === video.id && video.highlights && (
                  <div className="mt-4 space-y-3 animate-in slide-in-from-top-2 duration-300">
                    <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-purple-500" />
                      Generated Highlights
                    </h3>
                    {video.highlights.map((highlight) => (
                      <Card key={highlight.id} className="border border-purple-100 bg-gradient-to-r from-purple-50 to-white hover:shadow-md transition-all">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <h4 className="font-medium text-gray-900 mb-1">{highlight.title}</h4>
                              <div className="flex items-center gap-4 text-xs text-gray-600">
                                <span className="flex items-center gap-1">
                                  <Film className="h-3 w-3" />
                                  {highlight.duration}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Eye className="h-3 w-3" />
                                  {highlight.views} views
                                </span>
                                <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">
                                  {highlight.platform}
                                </span>
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <Button size="icon" variant="ghost" className="h-8 w-8">
                                <Play className="h-4 w-4" />
                              </Button>
                              <Button size="icon" variant="ghost" className="h-8 w-8">
                                <Download className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
                </div>
              ))}
            </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
