import { useScan } from '../context/ScanContext'
import VisualScanner from '../components/VisualScanner'
import { Camera } from 'lucide-react'

const VisualScannerPage = () => {
    const { updateStats, addFeedEvent, addScanRecord } = useScan()

    const handleScanComplete = (type, data, duration) => {
        const input = data.prediction || ''
        const risk = data.risk_score ?? 0

        updateStats(risk)
        addScanRecord(type, 'screenshot', data, duration)

        if (risk >= 70) {
            addFeedEvent(`⚠️ Phishing screenshot detected (risk: ${risk}%)`)
        } else if (risk >= 30) {
            addFeedEvent(`⚠️ Suspicious screenshot (risk: ${risk}%)`)
        } else {
            addFeedEvent(`✅ Safe screenshot (risk: ${risk}%)`)
        }
    }

    return (
        <div className="page-container">
            <div className="page-header animate-in">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border border-cyan-500/20 flex items-center justify-center">
                        <Camera size={20} className="text-cyan-400" />
                    </div>
                    <div>
                        <h1 className="page-title">Visual Phishing Scanner</h1>
                        <p className="page-subtitle">Analyze screenshots using CNN, OCR, and Brand Detection</p>
                    </div>
                </div>
            </div>

            <div className="max-w-2xl mx-auto">
                <VisualScanner onScanComplete={handleScanComplete} />
            </div>
        </div>
    )
}

export default VisualScannerPage
