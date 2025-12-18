import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sword, Mail, Lock, User, Gamepad2 } from 'lucide-react';
import { authService } from '../utils/api';

export const LoginPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    summoner_name: '',
    region: 'NA',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isLogin) {
        await authService.login(formData.username, formData.password);
        navigate('/draft');
      } else {
        await authService.register(formData);
        await authService.login(formData.username, formData.password);
        navigate('/draft');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-black p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-600 to-secondary-600 rounded-2xl mb-4">
            <Sword size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">TrynDraft</h1>
          <p className="text-gray-400 mt-2">Drafting Assistant for League of Legends</p>
        </div>

        {/* Form Card */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8">
          <div className="flex justify-center mb-6">
            <div className="flex bg-white/5 rounded-lg p-1">
              <button
                onClick={() => setIsLogin(true)}
                className={`px-6 py-2 rounded transition-all ${
                  isLogin 
                    ? 'bg-primary-600 text-white' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Login
              </button>
              <button
                onClick={() => setIsLogin(false)}
                className={`px-6 py-2 rounded transition-all ${
                  !isLogin 
                    ? 'bg-primary-600 text-white' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Sign Up
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
                    placeholder="your@email.com"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-400 mb-2">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  required
                  className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
                  placeholder="username"
                />
              </div>
            </div>

            {!isLogin && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Summoner Name (Optional)</label>
                <div className="relative">
                  <Gamepad2 className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
                  <input
                    type="text"
                    name="summoner_name"
                    value={formData.summoner_name}
                    onChange={handleChange}
                    className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
                    placeholder="Your League name"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-400 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {!isLogin && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Region</label>
                <select
                  name="region"
                  value={formData.region}
                  onChange={handleChange}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="NA">NA</option>
                  <option value="EUW">EUW</option>
                  <option value="EUNE">EUNE</option>
                  <option value="KR">KR</option>
                  <option value="BR">BR</option>
                  <option value="LAN">LAN</option>
                  <option value="LAS">LAS</option>
                  <option value="OCE">OCE</option>
                  <option value="RU">RU</option>
                  <option value="TR">TR</option>
                  <option value="JP">JP</option>
                </select>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-primary-600 to-secondary-600 text-white py-3 rounded-lg font-medium hover:from-primary-700 hover:to-secondary-700 transition-all disabled:opacity-50"
            >
              {loading ? 'Loading...' : (isLogin ? 'Login' : 'Create Account')}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              to="/draft"
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              Continue as Guest →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};