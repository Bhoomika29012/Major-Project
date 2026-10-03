import { useState, useMemo } from 'react'
import { useScan } from '../context/ScanContext'
import { Clock, Search, Trash2, Shield, AlertTriangle, ShieldCheck, ArrowUpDown, ChevronRight, ChevronDown, MessageSquare, QrCode, Camera } from 'lucide-react'
import RiskMeter from '../components/RiskMeter'
import { calculateRisk } from '../utils/risk'
import { generateExplanations } from '../utils/explain'

const typeFilters = ['all', 'url', 'sms', 'qr', 'visual']
const riskFilters = ['all', 'safe', 'suspicious', 'phishing']

const ScanHistory = () => {
    const { scanHistory, clearHistory } = useScan()
    const [search, setSearch] = useState('')
    const [typeFilter, setTypeFilter] = useState('all')
    const [riskFilter, setRiskFilter] = useState('all')
    const [sortOrder, setSortOrder] = useState('newest')
    const [expandedId, setExpandedId] = useState(null)

    const filtered = useMemo(() => {
        let items = [...scanHistory]

        if (search) {
            const q = search.toLowerCase()
            items = items.filter(item => item.input?.toLowerCase().includes(q))
        }

        if (typeFilter !== 'all') {
            items = items.filter(item => item.type === typeFilter)
        }

        if (riskFilter !== 'all') {
            items = items.filter(item => {
                const risk = item.risk || 0
                if (riskFilter === 'safe') return risk < 30
                if (riskFilter === 'suspicious') return risk >= 30 && risk < 70
                if (riskFilter === 'phishing') return risk >= 70
                return true
            })
        }

        items.sort((a, b) => {
            const da = new Date(a.timestamp).getTime()
            const db = new Date(b.timestamp).getTime()
            return sortOrder === 'newest' ? db - da : da - db
        })

        return items
    }, [scanHistory, search, typeFilter, riskFilter, sortOrder])

    const getTypeIcon = (type) => {
        switch (type) {
            case 'url': return <Search size={14} />
            case 'sms': return <MessageSquare size={14} />
            case 'qr': return <QrCode size={14} />
            case 'visual': return <Camera size={14} />
            default: return <Clock size={14} />
        }
    }

    const getRiskBadge = (risk) => {
        if (risk >= 70) return { label: 'Phishing', color: 'bg-red-500/15 text-red-400 border-red-500/20' }
        if (risk >= 30) return { label: 'Suspicious', color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20' }
        return { label: 'Safe', color: 'bg-green-500/15 text-green-400 border-green-500/20' }
    }

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-primary-500/20 to-primary-600/10 border border-primary-500/20 flex items-center justify-center">
                            <Clock size={20} className="text-primary-400" />
                        </div>
                        <div>
                            <h1 className="page-title">Scan History</h1>
                            <p className="page-subtitle">{scanHistory.length} total scans recorded</p>
                        </div>
                    </div>
                    {scanHistory.length > 0 && (
                        <button onClick={clearHistory} className="btn-secondary flex items-center gap-2 text-xs">
                            <Trash2 size={14} />
                            Clear All
                        </button>
                    )}
                </div>
            </div>

            {/* Filters */}
            <div className="glass rounded-2xl p-4 mb-6 animate-in">
                <div className="flex flex-wrap gap-3 items-center">
                    <div className="relative flex-1 min-w-[200px]">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input
                            type="text"
                            className="input-modern pl-9 py-2.5 text-xs"
                            placeholder="Search by URL or message..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>

                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase">Type</span>
                        <div className="flex gap-1">
                            {typeFilters.map(f => (
                                <button
                                    key={f}
                                    onClick={() => setTypeFilter(f)}
                                    className={`px-3 py-1.5 rounded-lg text-[10px] font-semibold uppercase transition-all ${
                                        typeFilter === f
                                            ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20'
                                            : 'text-slate-500 hover:text-slate-300 border border-transparent'
                                    }`}
                                >
                                    {f}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-500 font-semibold uppercase">Risk</span>
                        <div className="flex gap-1">
                            {riskFilters.map(f => (
                                <button
                                    key={f}
                                    onClick={() => setRiskFilter(f)}
                                    className={`px-3 py-1.5 rounded-lg text-[10px] font-semibold uppercase transition-all ${
                                        riskFilter === f
                                            ? 'bg-primary-500/15 text-primary-400 border border-primary-500/20'
                                            : 'text-slate-500 hover:text-slate-300 border border-transparent'
                                    }`}
                                >
                                    {f}
                                </button>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={() => setSortOrder(sortOrder === 'newest' ? 'oldest' : 'newest')}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold text-slate-500 hover:text-slate-300 border border-transparent hover:border-slate-700/30 transition-all"
                    >
                        <ArrowUpDown size={12} />
                        {sortOrder === 'newest' ? 'Newest' : 'Oldest'}
                    </button>
                </div>
            </div>

            {/* Results */}
            {filtered.length === 0 ? (
                <div className="glass rounded-2xl p-12 text-center animate-in">
                    <Clock size={40} className="text-slate-700 mx-auto mb-4" />
                    <p className="text-sm text-slate-500 font-medium">No scan history found</p>
                    <p className="text-xs text-slate-600 mt-1">
                        {search ? 'Try a different search term' : 'Run a scan to start building your history'}
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {filtered.map((item, idx) => {
                        const badge = getRiskBadge(item.risk)
                        const isExpanded = expandedId === item.id
                        const risk = calculateRisk({ label: item.label, confidence: item.confidence })
                        const explanations = generateExplanations({ label: item.label, explanation: item.explanation }, item.input)

                        return (
                            <div
                                key={item.id}
                                className={`glass rounded-2xl overflow-hidden transition-all duration-200 animate-in ${isExpanded ? 'ring-1 ring-primary-500/20' : ''}`}
                                style={{ animationDelay: `${idx * 30}ms` }}
                            >
                                <div
                                    className="px-5 py-4 flex items-center gap-4 cursor-pointer hover:bg-slate-800/30 transition-colors"
                                    onClick={() => setExpandedId(isExpanded ? null : item.id)}
                                >
                                    <div className={`h-8 w-8 rounded-lg bg-slate-800/50 border border-slate-700/30 flex items-center justify-center shrink-0 ${
                                        item.type === 'url' ? 'text-primary-400' : item.type === 'sms' ? 'text-violet-400' : item.type === 'qr' ? 'text-emerald-400' : 'text-cyan-400'
                                    }`}>
                                        {getTypeIcon(item.type)}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs text-slate-300 truncate font-mono">
                                            {item.input || '(no input)'}
                                        </p>
                                        <div className="flex items-center gap-3 mt-1">
                                            <span className="text-[10px] text-slate-500">
                                                {new Date(item.timestamp).toLocaleDateString()} {new Date(item.timestamp).toLocaleTimeString()}
                                            </span>
                                            {item.duration && (
                                                <span className="text-[10px] text-slate-600">
                                                    {(item.duration / 1000).toFixed(1)}s
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        <span className={`badge text-[10px] ${badge.color}`}>
                                            {badge.label}
                                        </span>
                                        <ChevronRight size={14} className={`text-slate-500 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="px-5 pb-5 border-t border-slate-700/30 pt-4 animate-in space-y-4">
                                        <RiskMeter riskValue={risk} />

                                        {item.threat_intel && (
                                            <div className="bg-slate-900/40 border border-slate-700/30 rounded-xl p-3">
                                                <p className="text-[10px] text-slate-500 font-semibold mb-1">Threat Intelligence</p>
                                                <p className="text-xs text-slate-400">
                                                    Risk Score: {Math.round((item.threat_intel.final_risk_score || 0) * 100)}%
                                                </p>
                                            </div>
                                        )}

                                        {explanations.length > 0 && (
                                            <div className="space-y-1.5">
                                                <p className="text-[10px] text-slate-500 font-semibold">Detection Factors</p>
                                                {explanations.slice(0, 3).map((exp, i) => (
                                                    <div key={i} className="flex items-center gap-2 text-xs text-slate-500">
                                                        <span>{exp.emoji}</span>
                                                        <span>{exp.title}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
export default ScanHistory
