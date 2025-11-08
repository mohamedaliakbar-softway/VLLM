import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  Video, Play, Trash2, Download, Calendar, TrendingUp, ArrowLeft, 
  BarChart3, Plus, Sparkles, Film, Share2, X, User, Settings, LogOut
} from 'lucide-react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

function Dashboard() {
  const [videos, setVideos] = useState([]);
  const [exportedClips, setExportedClips] = useState([]); // Clips from export
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState(null);
  const [timelineFilter, setTimelineFilter] = useState('all');
  const [expandedVideo, setExpandedVideo] = useState(null);
  const [user, setUser] = useState(null);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [stats, setStats] = useState({
    totalVideos: 0,
    totalShorts: 0,
    totalViews: 0,
    avgEngagement: 0
  });
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Check if user is logged in
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }

    // Check if coming from export
    if (location.state?.fromExport && location.state?.exportedClips) {
      setExportedClips(location.state.exportedClips);
      // Clear the location state to prevent re-triggering on refresh
      navigate(location.pathname, { replace: true, state: {} });
    }
    
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/projects');
      const projects = response.data;
      
      // Transform projects to match the expected format
      const transformedVideos = projects.map(project => ({
        id: project.id,
        title: project.video_title || 'Untitled Video',
        thumbnail: `https://img.youtube.com/vi/${project.video_id}/maxresdefault.jpg`,
        createdAt: new Date(project.created_at).toLocaleDateString(),
        shorts: project.shorts?.length || 0,
        highlights: project.shorts?.map((short, idx) => ({
          id: short.id,
          title: short.title || `Highlight ${idx + 1}`,
          duration: `${short.duration || 30}s`,
          platform: short.platform || 'YouTube Shorts',
          filename: short.filename,
          download_url: short.download_url || `/api/v1/download/${short.filename}`
        })) || [],
        status: project.status,
        processingTime: 'N/A'
      }));
      
      setVideos(transformedVideos);
      
      // Calculate stats
      const totalShorts = transformedVideos.reduce((sum, v) => sum + v.shorts, 0);
      setStats({
        totalVideos: transformedVideos.length,
        totalShorts: totalShorts + exportedClips.length,
        totalViews: 0,
        avgEngagement: 0
      });
      
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (videoId) => {
    if (globalThis.confirm('Are you sure you want to delete this video and all its shorts?')) {
      try {
        // Delete project from backend
        await axios.delete(`/api/v1/projects/${videoId}`);
        
        // Update local state
        setVideos(videos.filter(v => v.id !== videoId));
        
        // Refresh stats
        await fetchProjects();
      } catch (error) {
        console.error('Error deleting project:', error);
        globalThis.alert('Failed to delete project. Please try again.');
      }
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

  const handleShareClip = (clip) => {
    // Navigate to editor with clip data for sharing
    navigate('/editor', { 
      state: { 
        shareClip: clip,
        youtubeUrl: clip.youtubeUrl
      } 
    });
  };

  const handleRemoveExportedClip = (clipId) => {
    setExportedClips(exportedClips.filter(clip => clip.id !== clipId));
    
    // Update stats
    setStats(prev => ({
      ...prev,
      totalShorts: prev.totalShorts - 1
    }));
  };

  const handleTimelineFilter = (filter) => {
    setTimelineFilter(filter);
    // Here you would filter videos based on the timeline
    // For now, we'll just update the state
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    setUser(null);
    setShowProfileMenu(false);
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Enhanced Header */}
      <div className="border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#1E201E] rounded-lg flex items-center justify-center">
                <Video className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-gray-900">HighlightAI</span>
            </div>
            
            <div className="flex items-center gap-3">
              <Sparkles className="h-6 w-6 text-[#1E201E]" />
              <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
            </div>
            
            <div className="flex items-center gap-3">
              <Button className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white" onClick={() => navigate('/')}>
                <Plus className="h-4 w-4" />
                Create New
              </Button>

              {user && (
                <div className="relative">
                  <button
                    onClick={() => setShowProfileMenu(!showProfileMenu)}
                    className="flex items-center gap-2 hover:bg-gray-100 rounded-lg px-3 py-2 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#1E201E] to-gray-700 flex items-center justify-center text-white text-sm font-bold">
                      {user.avatar ? (
                        <img src={user.avatar} alt="Profile" className="w-full h-full rounded-full object-cover" />
                      ) : (
                        user.name?.charAt(0).toUpperCase() || 'U'
                      )}
                    </div>
                  </button>

                  {showProfileMenu && (
                    <>
                      <div 
                        className="fixed inset-0 z-10" 
                        onClick={() => setShowProfileMenu(false)}
                      />
                      <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-20">
                        <div className="px-4 py-3 border-b border-gray-100">
                          <p className="text-sm font-medium text-gray-900">{user.name}</p>
                          <p className="text-xs text-gray-600 truncate">{user.email}</p>
                        </div>
                        <Link
                          to="/profile"
                          className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => setShowProfileMenu(false)}
                        >
                          <User className="h-4 w-4" />
                          Profile
                        </Link>
                        <Link
                          to="/settings"
                          className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => setShowProfileMenu(false)}
                        >
                          <Settings className="h-4 w-4" />
                          Settings
                        </Link>
                        <div className="border-t border-gray-100 mt-2 pt-2">
                          <button
                            onClick={handleLogout}
                            className="flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                          >
                            <LogOut className="h-4 w-4" />
                            Logout
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
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
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center">
                  <Download className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Exported Clips</p>
                  <p className="text-2xl font-bold text-gray-900">{exportedClips.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Ready to Share</p>
                  <p className="text-2xl font-bold text-gray-900">{exportedClips.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Exported Clips Section */}
        {exportedClips.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <Sparkles className="h-6 w-6 text-purple-600" />
                  Exported Clips
                </h3>
                <p className="text-gray-600 mt-1">Your recently exported video shorts ready to download or share</p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
              {exportedClips.map((clip) => (
                <Card key={clip.id} className="overflow-hidden hover:shadow-xl transition-all duration-300 border-2 border-purple-200 bg-gradient-to-br from-purple-50 to-white">
                  {/* Clip Thumbnail */}
                  <div className="relative aspect-video bg-gradient-to-br from-purple-100 to-pink-100 overflow-hidden">
                    <img 
                      src={clip.thumbnail} 
                      alt={clip.title} 
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent flex items-end p-4">
                      <div className="text-white">
                        <p className="text-xs font-medium mb-1">Duration: {clip.duration}s</p>
                        <p className="text-xs opacity-80">{clip.startTime} - {clip.endTime}</p>
                      </div>
                    </div>
                    {/* Export Badge */}
                    <div className="absolute top-3 right-3">
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-purple-600 text-white shadow-lg">
                        ✨ Exported
                      </span>
                    </div>
                    {/* Remove button */}
                    <Button
                      size="icon"
                      variant="ghost"
                      className="absolute top-3 left-3 h-8 w-8 bg-white/90 hover:bg-white"
                      onClick={() => handleRemoveExportedClip(clip.id)}
                    >
                      <X className="h-4 w-4 text-gray-700" />
                    </Button>
                  </div>

                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg line-clamp-2">{clip.title}</CardTitle>
                  </CardHeader>

                  <CardContent className="pt-0 space-y-3">
                    {/* Clip Info */}
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Film className="h-4 w-4" />
                      <span>Ready for download</span>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-2">
                      <Button 
                        className="flex-1 bg-purple-600 hover:bg-purple-700 text-white"
                        onClick={() => handleDownload(clip)}
                        disabled={downloadingId === clip.id}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        {downloadingId === clip.id ? 'Downloading...' : 'Download'}
                      </Button>
                      <Button 
                        variant="outline"
                        className="flex-1 border-purple-300 text-purple-700 hover:bg-purple-50"
                        onClick={() => handleShareClip(clip)}
                      >
                        <Share2 className="h-4 w-4 mr-2" />
                        Share
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

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
                                <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">
                                  {highlight.platform}
                                </span>
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <Button size="icon" variant="ghost" className="h-8 w-8">
                                <Play className="h-4 w-4" />
                              </Button>
                              <Button 
                                size="icon" 
                                variant="ghost" 
                                className="h-8 w-8"
                                onClick={() => handleDownload({ 
                                  id: highlight.id, 
                                  title: highlight.title,
                                  download_url: highlight.download_url,
                                  filename: highlight.filename
                                })}
                              >
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
