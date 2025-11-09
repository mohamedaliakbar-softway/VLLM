import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, ArrowLeft, Bell, Shield, Palette, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

function Settings() {
  const [user, setUser] = useState(null);
  const [settings, setSettings] = useState({
    emailNotifications: true,
    pushNotifications: false,
    darkMode: false,
    autoSave: true
  });
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    } else {
      navigate('/signin');
    }

    // Load settings
    const savedSettings = localStorage.getItem('settings');
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
  }, [navigate]);

  const handleToggle = (key) => {
    const newSettings = {
      ...settings,
      [key]: !settings[key]
    };
    setSettings(newSettings);
    localStorage.setItem('settings', JSON.stringify(newSettings));
    setSuccess(true);
    setTimeout(() => setSuccess(false), 3000);
  };

  const handleDeleteAccount = () => {
    if (window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      localStorage.removeItem('user');
      localStorage.removeItem('settings');
      navigate('/');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/');
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <nav className="border-b border-gray-200 bg-white/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="h-5 w-5" />
              Back to Dashboard
            </button>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#1E201E] rounded-lg flex items-center justify-center">
                <Video className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-gray-900">Zapp.ai</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Settings Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600 mt-2">Manage your preferences and account settings</p>
        </div>

        {success && (
          <Alert className="mb-6 border-green-200 bg-green-50">
            <AlertDescription className="text-green-800">
              Settings saved successfully!
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-6">
          {/* Notifications */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Bell className="h-5 w-5 text-gray-600" />
                <div>
                  <CardTitle>Notifications</CardTitle>
                  <CardDescription>Manage how you receive notifications</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Email notifications</p>
                  <p className="text-sm text-gray-600">Receive updates via email</p>
                </div>
                <button
                  onClick={() => handleToggle('emailNotifications')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.emailNotifications ? 'bg-[#1E201E]' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.emailNotifications ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Push notifications</p>
                  <p className="text-sm text-gray-600">Receive push notifications</p>
                </div>
                <button
                  onClick={() => handleToggle('pushNotifications')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.pushNotifications ? 'bg-[#1E201E]' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.pushNotifications ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </CardContent>
          </Card>

          {/* Appearance */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Palette className="h-5 w-5 text-gray-600" />
                <div>
                  <CardTitle>Appearance</CardTitle>
                  <CardDescription>Customize how the app looks</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Dark mode</p>
                  <p className="text-sm text-gray-600">Use dark theme</p>
                </div>
                <button
                  onClick={() => handleToggle('darkMode')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.darkMode ? 'bg-[#1E201E]' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.darkMode ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </CardContent>
          </Card>

          {/* Privacy & Security */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-gray-600" />
                <div>
                  <CardTitle>Privacy & Security</CardTitle>
                  <CardDescription>Manage your account security</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">Auto-save</p>
                  <p className="text-sm text-gray-600">Automatically save your work</p>
                </div>
                <button
                  onClick={() => handleToggle('autoSave')}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.autoSave ? 'bg-[#1E201E]' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.autoSave ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              <div className="pt-4 border-t">
                <Button
                  onClick={handleLogout}
                  variant="outline"
                  className="w-full border-gray-300 hover:bg-gray-50"
                >
                  Logout
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-red-200">
            <CardHeader>
              <div className="flex items-center gap-3">
                <Trash2 className="h-5 w-5 text-red-600" />
                <div>
                  <CardTitle className="text-red-600">Danger Zone</CardTitle>
                  <CardDescription>Irreversible actions</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Button
                onClick={handleDeleteAccount}
                variant="outline"
                className="w-full border-red-300 text-red-600 hover:bg-red-50"
              >
                Delete Account
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Settings;
