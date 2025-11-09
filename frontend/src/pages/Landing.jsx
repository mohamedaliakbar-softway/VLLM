import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Video, Sparkles, ArrowRight, Zap, Clock, Share2, Sun, Moon, User, Settings, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

function Landing() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [user, setUser] = useState(null);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is logged in
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }

    // Check dark mode preference
    const settings = localStorage.getItem('settings');
    if (settings) {
      const { darkMode: isDark } = JSON.parse(settings);
      setDarkMode(isDark);
    }
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    
    // Validate YouTube URL format
    if (!youtubeUrl.includes('youtube.com') && !youtubeUrl.includes('youtu.be')) {
      setError('Please enter a valid YouTube URL');
      return;
    }

    // Redirect to editor with YouTube URL - processing will happen there
    navigate('/editor', { state: { youtubeUrl } });
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    setUser(null);
    setShowProfileMenu(false);
  };

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    const settings = JSON.parse(localStorage.getItem('settings') || '{}');
    settings.darkMode = newMode;
    localStorage.setItem('settings', JSON.stringify(settings));
  };

  return (
    <div className="min-h-screen bg-white relative overflow-hidden">
      {/* Circular Gradient Background Loader */}
      <div className="loader-wrapper loader-wrapper-home">
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <div className="loader"></div>
      </div>

      {/* Navigation Bar */}
      <nav className="border-b border-gray-200 bg-white/80 backdrop-blur-sm relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#1E201E] rounded-lg flex items-center justify-center">
                <Video className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">Zapp.ai</span>
            </div>

            {/* Center Navigation */}
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Features</a>
              <a href="#demos" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Demos</a>
              <a href="#architecture" className="text-sm text-gray-600 hover:text-gray-900 font-medium">Architecture</a>
              <button className="text-sm text-gray-600 hover:text-gray-900 font-medium flex items-center gap-1">
                <Sparkles className="h-4 w-4" />
                Agent Dashboard
              </button>
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-3">
              {/* Theme Toggle */}
              <button
                onClick={toggleDarkMode}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Toggle theme"
              >
                {darkMode ? <Sun className="h-5 w-5 text-gray-600" /> : <Moon className="h-5 w-5 text-gray-600" />}
              </button>

              {/* Divider */}
              <div className="h-6 w-px bg-gray-300" />

              {user ? (
                /* User Profile Menu */
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
                    <span className="text-sm font-medium text-gray-900 hidden sm:block">{user.name}</span>
                  </button>

                  {/* Dropdown Menu */}
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
              ) : (
                /* Login/Signup Buttons */
                <>
                  <Link to="/signin">
                    <Button variant="ghost" className="text-gray-700 hover:text-gray-900">
                      Login
                    </Button>
                  </Link>
                  <Link to="/signup">
                    <Button className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white">
                      Sign Up
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 text-center relative z-10">
        <Badge variant="outline" className="mb-8 inline-flex items-center gap-2 border-gray-300 text-gray-700">
          <Sparkles className="h-4 w-4" />
          AI-Powered Video Highlights
        </Badge>
        
        <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 mb-6">
          Transform Videos into
          <div className="relative mt-4 max-w-2xl mx-auto">
            {/* Liquid Glass Container */}
            <div className="relative rounded-2xl overflow-hidden backdrop-blur-2xl bg-gradient-to-br from-[#1E201E]/90 via-[#1E201E]/80 to-black/90 border border-white/20 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]">
              {/* Background pattern for glass effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-black/20 via-gray-900/30 to-black/20"></div>
              
              {/* Animated liquid effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-transparent via-white/5 to-transparent opacity-40"></div>
              
              {/* Shimmer shine effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent transform -skew-x-12 landing-shimmer"></div>
              
              {/* Inner glow */}
              <div className="absolute inset-[1px] rounded-2xl bg-gradient-to-b from-white/5 to-transparent"></div>
              
              {/* Highlights text */}
              <div className="relative h-full flex items-center justify-center z-10">
                <span className="relative text-3xl sm:text-4xl font-bold inline-block">
                  {/* Main text with liquid glass effect */}
                  <span 
                    className="relative z-10 text-white"
                    style={{
                      textShadow: `
                        0 0 10px rgba(255, 255, 255, 0.5),
                        0 0 20px rgba(255, 255, 255, 0.3),
                        0 0 30px rgba(255, 255, 255, 0.2),
                        0 2px 4px rgba(0, 0, 0, 0.3)
                      `,
                      filter: 'blur(0.5px)',
                      WebkitTextStroke: '0.5px rgba(255, 255, 255, 0.3)'
                    }}
                  >
                    Highlights
                  </span>
                  {/* Animated glass shine overlay */}
                  <span 
                    className="absolute inset-0 text-white/60 pointer-events-none overflow-hidden"
                    style={{
                      background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent)',
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      transform: 'skewX(-12deg)',
                      animation: 'shimmer 3s infinite'
                    }}
                  >
                    Highlights
                  </span>
                  {/* Glow layer behind text */}
                  <span 
                    className="absolute inset-0 text-white/20 blur-md -z-10"
                  >
                    Highlights
                  </span>
                </span>
              </div>
            </div>
          </div>
        </h1>

        <p className="text-lg sm:text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
          Paste any YouTube URL and let our advanced AI extract the most
          <br className="hidden sm:block" />
          engaging moments in seconds. Perfect for creating Shorts, Reels, and TikToks.
        </p>

        {/* URL Input */}
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto mb-6">
          <div className="flex flex-col sm:flex-row gap-3 p-1 bg-gray-50 rounded-xl border border-gray-200">
            <Input
              type="url"
              placeholder="https://youtube.com/watch?v=..."
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              required
              disabled={loading}
              className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
            />
            <Button 
              type="submit" 
              disabled={!youtubeUrl || loading} 
              className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white whitespace-nowrap"
            >
              <Sparkles className="h-4 w-4" />
              Generate
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </form>

        {error && (
          <Alert variant="destructive" className="max-w-2xl mx-auto mb-6 border-red-200 bg-red-50">
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-center gap-2 text-sm text-gray-500 mb-12">
          <div className="text-green-600 font-bold">✓</div>
          <span>No credit card required • Free trial available</span>
        </div>

        {/* Feature Highlights */}
        <div className="flex flex-wrap items-center justify-center gap-8">
          <div className="flex items-center gap-2 text-gray-700">
            <Zap className="h-5 w-5 text-[#1E201E]" />
            <span className="text-sm font-medium">AI-Powered Detection</span>
          </div>
          <div className="flex items-center gap-2 text-gray-700">
            <Clock className="h-5 w-5 text-[#1E201E]" />
            <span className="text-sm font-medium">2-Minute Processing</span>
          </div>
          <div className="flex items-center gap-2 text-gray-700">
            <Share2 className="h-5 w-5 text-[#1E201E]" />
            <span className="text-sm font-medium">Multi-Platform Export</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
