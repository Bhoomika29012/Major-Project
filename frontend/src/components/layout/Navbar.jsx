import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../utils/AuthContext'
import {
    Shield, Home, Search, MessageSquare, QrCode, Camera,
    Clock, User, LogOut, Menu, X, ChevronDown
} from 'lucide-react'

const navItems = [
    { label: 'Home', path: '/', icon: Home },
    { label: 'URL Scanner', path: '/url-scanner', icon: Search },
    { label: 'SMS Scanner', path: '/sms-scanner', icon: MessageSquare },
    { label: 'QR Scanner', path: '/qr-scanner', icon: QrCode },
    { label: 'Visual Scanner', path: '/visual-scanner', icon: Camera },
    { label: 'Scan History', path: '/history', icon: Clock },
    { label: 'Profile', path: '/profile', icon: User },
]

const Navbar = () => {
    const { user, logout } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()
    const [mobileOpen, setMobileOpen] = useState(false)
    const [profileOpen, setProfileOpen] = useState(false)

    const handleLogout = () => {
        setProfileOpen(false)
        logout()
        navigate('/login')
    }

    const isActive = (path) => {
        if (path === '/') return location.pathname === '/'
        return location.pathname.startsWith(path)
    }

    return (
        <nav className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">

                    {/* Logo */}
                    <button onClick={() => navigate('/')} className="flex items-center gap-3 group">
                        <div className="relative">
                            <Shield className="text-primary-400 group-hover:text-primary-300 transition-colors" size={28} />
                            <div className="absolute -inset-1 bg-primary-400/20 rounded-full blur-sm -z-10 group-hover:bg-primary-400/30 transition-all" />
                        </div>
                        <div className="hidden sm:block">
                            <h1 className="text-lg font-bold tracking-tight">
                                <span className="text-gradient">CyberSentinel</span>
                            </h1>
                            <p className="text-[9px] text-slate-500 font-medium tracking-widest uppercase leading-tight">AI Threat Detection</p>
                        </div>
                    </button>

                    {/* Desktop Nav */}
                    <div className="hidden lg:flex items-center gap-1">
                        {navItems.map((item) => {
                            const active = isActive(item.path)
                            const Icon = item.icon
                            return (
                                <button
                                    key={item.path}
                                    onClick={() => { navigate(item.path); setMobileOpen(false) }}
                                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all duration-200 ${
                                        active
                                            ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20'
                                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                                    }`}
                                >
                                    <Icon size={15} />
                                    {item.label}
                                </button>
                            )
                        })}
                    </div>

                    {/* Profile / Mobile Toggle */}
                    <div className="flex items-center gap-3">
                        {/* Desktop Profile */}
                        <div className="hidden lg:block relative">
                            <button
                                onClick={() => setProfileOpen(!profileOpen)}
                                className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-800/50 border border-slate-700/30 hover:bg-slate-700/50 hover:border-slate-600/50 transition-all duration-200"
                            >
                                <div className="h-6 w-6 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
                                    <User size={12} className="text-white" />
                                </div>
                                <span className="text-sm font-medium text-slate-200 max-w-[100px] truncate">{user?.name}</span>
                                <ChevronDown size={12} className={`text-slate-500 transition-transform duration-200 ${profileOpen ? 'rotate-180' : ''}`} />
                            </button>

                            {profileOpen && (
                                <>
                                    <div className="fixed inset-0 z-10" onClick={() => setProfileOpen(false)} />
                                    <div className="absolute right-0 top-full mt-2 w-48 glass rounded-xl p-1.5 z-20 animate-in-fast shadow-2xl">
                                        <button
                                            onClick={() => { navigate('/profile'); setProfileOpen(false) }}
                                            className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-xs text-slate-300 hover:bg-slate-700/50 transition-colors"
                                        >
                                            <User size={14} />
                                            Profile
                                        </button>
                                        <button
                                            onClick={() => { navigate('/history'); setProfileOpen(false) }}
                                            className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-xs text-slate-300 hover:bg-slate-700/50 transition-colors"
                                        >
                                            <Clock size={14} />
                                            Scan History
                                        </button>
                                        <hr className="border-slate-700/50 my-1" />
                                        <button
                                            onClick={handleLogout}
                                            className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                                        >
                                            <LogOut size={14} />
                                            Logout
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Mobile Toggle */}
                        <button
                            onClick={() => setMobileOpen(!mobileOpen)}
                            className="lg:hidden h-9 w-9 rounded-xl bg-slate-800/50 border border-slate-700/30 flex items-center justify-center hover:bg-slate-700/50 transition-colors"
                        >
                            {mobileOpen ? <X size={18} className="text-slate-400" /> : <Menu size={18} className="text-slate-400" />}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile Menu */}
            {mobileOpen && (
                <div className="lg:hidden border-t border-slate-800/50 animate-in-fast">
                    <div className="max-w-7xl mx-auto px-4 py-3 space-y-1">
                        {navItems.map((item) => {
                            const active = isActive(item.path)
                            const Icon = item.icon
                            return (
                                <button
                                    key={item.path}
                                    onClick={() => { navigate(item.path); setMobileOpen(false) }}
                                    className={`flex items-center gap-3 w-full px-3.5 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                                        active
                                            ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20'
                                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                                    }`}
                                >
                                    <Icon size={18} />
                                    {item.label}
                                </button>
                            )
                        })}
                        <hr className="border-slate-700/50 my-2" />
                        <div className="flex items-center gap-3 px-3.5 py-3">
                            <div className="h-7 w-7 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
                                <User size={12} className="text-white" />
                            </div>
                            <span className="text-sm text-slate-300 flex-1">{user?.name}</span>
                            <button onClick={handleLogout} className="text-slate-500 hover:text-red-400 transition-colors">
                                <LogOut size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </nav>
    )
}

export default Navbar
