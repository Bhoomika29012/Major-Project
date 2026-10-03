import { useState, useEffect } from 'react'
import { useAuth } from '../utils/AuthContext'
import { useScan } from '../context/ScanContext'
import { useNavigate } from 'react-router-dom'
import AttackStats from '../components/AttackStats'
import ThreatFeed from '../components/ThreatFeed'
import QuickActionCard from '../components/ui/QuickActionCard'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { Search, MessageSquare, QrCode, Camera, Activity } from 'lucide-react'

const Dashboard = () => {
    const { user } = useAuth()
    const { stats, feedEvents } = useScan()
    const navigate = useNavigate()
    const [greeting, setGreeting] = useState('')

    useEffect(() => {
        const hour = new Date().getHours()
        if (hour < 12) setGreeting('Good morning')
        else if (hour < 18) setGreeting('Good afternoon')
        else setGreeting('Good evening')
    }, [])

    return (
        <div className="page-container">
            {/* Welcome Section */}
            <div className="mb-8 animate-in">
                <div className="glass rounded-2xl p-6 md:p-8 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 via-transparent to-transparent pointer-events-none" />
                    <div className="relative">
                        <p className="text-sm text-slate-400 font-medium">{greeting},</p>
                        <h1 className="text-2xl md:text-3xl font-bold text-white mt-1">
                            <span className="text-gradient">{user?.name}</span>
                        </h1>
                        <p className="text-sm text-slate-400 mt-2 max-w-xl">
                            Welcome to your cybersecurity dashboard. Scan URLs, messages, and QR codes for phishing threats.
                        </p>
                        <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
                            <div className="flex items-center gap-1.5">
                                <Activity size={12} className="text-primary-400" />
                                <span>{stats.total} total scans</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Stats */}
            <AttackStats stats={stats} />

            {/* Quick Actions */}
            <div className="mb-8">
                <h2 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary-400" />
                    Quick Actions
                </h2>
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <QuickActionCard
                        title="URL Scanner"
                        description="Analyze URLs for phishing, malware, and suspicious patterns"
                        icon={Search}
                        to="/url-scanner"
                        gradient="from-primary-500 to-primary-600"
                        delay={0}
                    />
                    <QuickActionCard
                        title="SMS Scanner"
                        description="Detect smishing attacks and spam messages in real-time"
                        icon={MessageSquare}
                        to="/sms-scanner"
                        gradient="from-violet-500 to-violet-600"
                        delay={80}
                    />
                    <QuickActionCard
                        title="QR Scanner"
                        description="Upload QR code images to check for hidden malicious URLs"
                        icon={QrCode}
                        to="/qr-scanner"
                        gradient="from-emerald-500 to-emerald-600"
                        delay={160}
                    />
                    <QuickActionCard
                        title="Visual Scanner"
                        description="Analyze screenshots using AI vision, OCR & brand detection"
                        icon={Camera}
                        to="/visual-scanner"
                        gradient="from-cyan-500 to-cyan-600"
                        delay={240}
                    />
                </div>
            </div>

            {/* Threat Feed */}
            <div>
                <h2 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary-400" />
                    Recent Activity
                </h2>
                <ThreatFeed events={feedEvents} />
            </div>
        </div>
    )
}

export default Dashboard
