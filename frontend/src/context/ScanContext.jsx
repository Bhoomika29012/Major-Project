import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const ScanContext = createContext(null)

const STORAGE_KEY = 'cybersentinel_history'

export function useScan() {
    return useContext(ScanContext)
}

export function ScanProvider({ children }) {
    const [stats, setStats] = useState(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY + '_stats')
            return saved ? JSON.parse(saved) : { total: 0, safe: 0, suspicious: 0, phishing: 0 }
        } catch { return { total: 0, safe: 0, suspicious: 0, phishing: 0 } }
    })

    const [feedEvents, setFeedEvents] = useState(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY + '_events')
            return saved ? JSON.parse(saved) : []
        } catch { return [] }
    })

    const [scanHistory, setScanHistory] = useState(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY)
            return saved ? JSON.parse(saved) : []
        } catch { return [] }
    })

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(scanHistory.slice(0, 200)))
    }, [scanHistory])

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY + '_stats', JSON.stringify(stats))
    }, [stats])

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY + '_events', JSON.stringify(feedEvents.slice(0, 50)))
    }, [feedEvents])

    const updateStats = useCallback((risk) => {
        setStats(prev => {
            const newStats = { ...prev, total: prev.total + 1 }
            if (risk < 30) newStats.safe += 1
            else if (risk < 70) newStats.suspicious += 1
            else newStats.phishing += 1
            return newStats
        })
    }, [])

    const addFeedEvent = useCallback((message) => {
        const newEvent = {
            id: Date.now(),
            message,
            time: new Date().toLocaleTimeString()
        }
        setFeedEvents(prev => [newEvent, ...prev].slice(0, 50))
    }, [])

    const addScanRecord = useCallback((type, input, result, duration) => {
        const isVisual = type === 'visual'
        const label = isVisual ? (result?.prediction || 'unknown') : (result?.label || 'unknown')
        const confidence = isVisual ? ((result?.confidence || 0) / 100) : (result?.confidence || 0)
        const risk = isVisual
            ? (result?.risk_score || 0)
            : result?.label === 'phishing'
                ? (result.confidence || 0.5) * 100
                : (1 - (result.confidence || 0.5)) * 100
        const record = {
            id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
            type,
            input,
            label,
            confidence,
            risk,
            timestamp: new Date().toISOString(),
            duration: Math.round(duration),
            explanation: result?.explanation || [],
            threat_intel: result?.threat_intel || null,
        }
        setScanHistory(prev => [record, ...prev])
    }, [])

    const clearHistory = useCallback(() => {
        setScanHistory([])
        setStats({ total: 0, safe: 0, suspicious: 0, phishing: 0 })
        setFeedEvents([])
    }, [])

    return (
        <ScanContext.Provider value={{
            stats, feedEvents, scanHistory,
            updateStats, addFeedEvent, addScanRecord, clearHistory
        }}>
            {children}
        </ScanContext.Provider>
    )
}
