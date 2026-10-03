import React, { useState, useRef } from 'react'
import axios from 'axios'
import {
  Camera, Upload, Shield, AlertTriangle, ChevronRight, ChevronDown,
  RotateCw, Clock, BarChart3, Eye, FileText, Tag, X, Scan,
  BrainCircuit, Layers,
} from 'lucide-react'
import RiskMeter from './RiskMeter'
import { submitVisualScan } from '../services/visualScanService'

const VisualScanner = ({ onScanComplete }) => {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [scanDuration, setScanDuration] = useState(null)
  const [showExplanation, setShowExplanation] = useState(true)
  const [showOcrDetail, setShowOcrDetail] = useState(false)
  const [showBrandDetail, setShowBrandDetail] = useState(false)
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setPreview(URL.createObjectURL(selectedFile))
      setResult(null)
      setError(null)
    }
  }

  const clearFile = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
    setError(null)
    setScanDuration(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleScan = async (e) => {
    e.preventDefault()
    if (!file) return

    setLoading(true)
    setResult(null)
    setError(null)
    setShowExplanation(true)
    setShowOcrDetail(false)
    setShowBrandDetail(false)

    const startTime = performance.now()

    try {
      const data = await submitVisualScan(file)
      const duration = performance.now() - startTime
      setScanDuration(duration)
      setResult(data)

      if (onScanComplete) {
        onScanComplete('visual', data, duration)
      }
    } catch (err) {
      console.error('Visual scan failed:', err)
      const message = err.response?.data?.detail || err.message || 'Visual analysis failed'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const riskValue = result?.risk_score ?? 0

  const handleScanAgain = () => {
    setResult(null)
    setError(null)
    setShowExplanation(true)
    setScanDuration(null)
    clearFile()
  }

  return (
    <div className="space-y-4">

      {/* ── Upload Card ── */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border border-cyan-500/20 flex items-center justify-center">
            <Camera size={18} className="text-cyan-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-200">Visual Phishing Scanner</h2>
            <p className="text-[10px] text-slate-500">Analyze screenshots using CNN + OCR + Brand Detection</p>
          </div>
        </div>

        <form onSubmit={handleScan} className="space-y-3">
          {/* Upload Area */}
          <div className="relative">
            {preview ? (
              <div className="relative rounded-xl overflow-hidden border-2 border-dashed border-cyan-500/30 bg-slate-900/60">
                <img src={preview} alt="Screenshot Preview" className="w-full h-48 object-contain p-2" />
                <button
                  type="button"
                  onClick={clearFile}
                  className="absolute top-2 right-2 h-7 w-7 rounded-full bg-slate-900/80 border border-slate-700/50 flex items-center justify-center hover:bg-slate-800 transition-colors"
                >
                  <X size={14} className="text-slate-400" />
                </button>
                <div className="absolute bottom-2 left-2 right-2 text-center">
                  <span className="text-[10px] text-slate-500 bg-slate-900/80 px-2 py-1 rounded-full border border-slate-700/30">
                    {file?.name || 'Image loaded'}
                  </span>
                </div>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center w-full h-48 rounded-xl border-2 border-dashed border-slate-700/50 bg-slate-900/40 cursor-pointer hover:border-cyan-500/40 hover:bg-slate-900/60 transition-all duration-200 group">
                <div className="flex flex-col items-center justify-center">
                  <div className="h-12 w-12 rounded-xl bg-slate-800/80 border border-slate-700/50 flex items-center justify-center group-hover:border-cyan-500/30 group-hover:bg-slate-800 transition-all duration-200 mb-3">
                    <Upload className="w-5 h-5 text-slate-400 group-hover:text-cyan-400 transition-colors" />
                  </div>
                  <p className="text-sm font-medium text-slate-400 group-hover:text-slate-300 transition-colors">Upload Screenshot</p>
                  <p className="text-[10px] text-slate-600 mt-1">PNG, JPG, WEBP, BMP, GIF (max 20MB)</p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  onChange={handleFileChange}
                  accept="image/png,image/jpeg,image/webp,image/bmp,image/gif"
                />
              </label>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !file}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Analyzing with AI Pipeline...
              </>
            ) : (
              <>
                <Scan size={16} />
                Analyze Screenshot
              </>
            )}
          </button>
        </form>
      </div>

      {/* ── Error Display ── */}
      {error && (
        <div className="glass rounded-2xl p-6 border-l-[3px] border-red-500 bg-red-500/5 animate-in">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center shrink-0">
              <AlertTriangle className="text-red-500" size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-200">Analysis Failed</h3>
              <p className="text-xs text-slate-400 mt-1">{error}</p>
              <button onClick={handleScanAgain} className="btn-secondary mt-3 text-xs flex items-center gap-2">
                <RotateCw size={12} /> Try Again
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Results ── */}
      {result && (
        <div className={`card-result border-l-[3px] animate-in ${
          riskValue >= 70
            ? "bg-red-500/5 border-red-500"
            : riskValue >= 30
              ? "bg-yellow-500/5 border-yellow-500"
              : "bg-green-500/5 border-green-500"
        }`}>

          <div className="space-y-5">

            {/* ════ Header ════ */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {riskValue >= 70
                  ? <div className="h-10 w-10 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center"><AlertTriangle className="text-red-500" size={20} /></div>
                  : riskValue >= 30
                    ? <div className="h-10 w-10 rounded-xl bg-yellow-500/20 border border-yellow-500/30 flex items-center justify-center"><AlertTriangle className="text-yellow-500" size={20} /></div>
                    : <div className="h-10 w-10 rounded-xl bg-green-500/20 border border-green-500/30 flex items-center justify-center"><Shield className="text-green-500" size={20} /></div>
                }
                <div>
                  <h3 className="text-sm font-bold text-slate-200">Visual Analysis Result</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`badge text-[10px] ${
                      riskValue >= 70
                        ? "bg-red-500/15 text-red-400 border border-red-500/20"
                        : riskValue >= 30
                          ? "bg-yellow-500/15 text-yellow-400 border border-yellow-500/20"
                          : "bg-green-500/15 text-green-400 border border-green-500/20"
                    }`}>
                      {result.prediction?.toUpperCase() || (riskValue >= 70 ? "PHISHING" : riskValue >= 30 ? "SUSPICIOUS" : "SAFE")}
                    </span>
                    {scanDuration && (
                      <span className="text-[10px] text-slate-500 flex items-center gap-1">
                        <Clock size={10} />
                        {(scanDuration / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* ════ Risk Score + Confidence ════ */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-900/40 border border-slate-700/30 rounded-xl px-4 py-3">
                <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1">Risk Score</p>
                <p className={`text-lg font-bold font-mono ${
                  riskValue >= 70 ? 'text-red-400' : riskValue >= 30 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {riskValue}/100
                </p>
              </div>
              <div className="bg-slate-900/40 border border-slate-700/30 rounded-xl px-4 py-3">
                <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mb-1">Confidence</p>
                <p className="text-lg font-bold text-cyan-300 font-mono">
                  {result.confidence ?? (result.cnn?.confidence ?? 0)}%
                </p>
              </div>
            </div>

            <RiskMeter riskValue={riskValue} />

            {/* ════ Grad-CAM Heatmap ════ */}
            {result.gradcam?.image && (
              <div className="bg-slate-900/50 border border-slate-700/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Eye size={14} className="text-cyan-400" />
                  <p className="text-xs font-semibold text-cyan-400">Grad-CAM Heatmap</p>
                </div>
                <div className="rounded-xl overflow-hidden border border-slate-700/50 bg-slate-900/80">
                  <img
                    src={`data:image/png;base64,${result.gradcam.image}`}
                    alt="Grad-CAM Overlay"
                    className="w-full h-auto max-h-64 object-contain"
                  />
                </div>
                <p className="text-[10px] text-slate-500 mt-2 text-center">
                  CNN activation map showing regions the model focused on
                </p>
              </div>
            )}

            {/* ════ CNN Prediction ════ */}
            {result.cnn && (
              <div className="bg-slate-900/50 border border-slate-700/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <BrainCircuit size={14} className="text-cyan-400" />
                  <p className="text-xs font-semibold text-cyan-400">CNN Prediction (MobileNetV3)</p>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] text-slate-500">Prediction</p>
                    <p className={`text-sm font-bold font-mono ${
                      result.cnn.prediction === 'Phishing' ? 'text-red-400' : 'text-green-400'
                    }`}>
                      {result.cnn.prediction}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-slate-500">Confidence</p>
                    <p className="text-sm font-bold text-cyan-300 font-mono">
                      {result.cnn.confidence ?? 0}%
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* ════ OCR Results ════ */}
            {result.ocr && (
              <div className="bg-slate-900/50 border border-slate-700/30 rounded-xl p-4">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setShowOcrDetail(!showOcrDetail)}
                >
                  <div className="flex items-center gap-2">
                    <FileText size={14} className="text-cyan-400" />
                    <p className="text-xs font-semibold text-cyan-400">OCR Text Extraction</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`badge text-[10px] ${
                      result.ocr.risk_score === 'High' ? 'bg-red-500/15 text-red-400' :
                      result.ocr.risk_score === 'Medium' ? 'bg-yellow-500/15 text-yellow-400' :
                      'bg-green-500/15 text-green-400'
                    }`}>
                      {result.ocr.risk_score} Risk
                    </span>
                    {showOcrDetail ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
                  </div>
                </div>
                {showOcrDetail && (
                  <div className="mt-3 space-y-2 animate-in-fast">
                    {result.ocr.text ? (
                      <div className="bg-slate-900/60 border border-slate-700/30 rounded-lg px-3 py-2">
                        <p className="text-[10px] text-slate-500 mb-1">Extracted Text</p>
                        <p className="text-xs text-slate-300 font-mono leading-relaxed max-h-24 overflow-y-auto">
                          {result.ocr.text}
                        </p>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No text detected</p>
                    )}
                    {result.ocr.keywords?.length > 0 && (
                      <div>
                        <p className="text-[10px] text-slate-500 mb-1.5">
                          Suspicious Keywords ({result.ocr.keyword_count})
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {result.ocr.keywords.map((kw, i) => (
                            <span key={i} className="px-2 py-0.5 rounded-md bg-red-500/10 border border-red-500/20 text-[10px] text-red-300 font-mono">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ════ Brand Detection ════ */}
            {result.brand_detection && (
              <div className="bg-slate-900/50 border border-slate-700/30 rounded-xl p-4">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setShowBrandDetail(!showBrandDetail)}
                >
                  <div className="flex items-center gap-2">
                    <Tag size={14} className="text-cyan-400" />
                    <p className="text-xs font-semibold text-cyan-400">Brand Detection</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`badge text-[10px] ${
                      result.brand_detection.risk_score === 'High' ? 'bg-red-500/15 text-red-400' :
                      result.brand_detection.risk_score === 'Medium' ? 'bg-yellow-500/15 text-yellow-400' :
                      'bg-green-500/15 text-green-400'
                    }`}>
                      {result.brand_detection.risk_score} Risk
                    </span>
                    {showBrandDetail ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
                  </div>
                </div>
                {showBrandDetail && (
                  <div className="mt-3 space-y-2 animate-in-fast">
                    {result.brand_detection.brands?.length > 0 ? (
                      <div className="space-y-2">
                        {result.brand_detection.brands.map((brand, i) => (
                          <div key={i} className="flex items-center justify-between bg-slate-900/60 border border-slate-700/30 rounded-lg px-3 py-2">
                            <div className="flex items-center gap-2">
                              <div className="h-6 w-6 rounded-md bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center">
                                <Tag size={11} className="text-yellow-400" />
                              </div>
                              <span className="text-xs font-semibold text-slate-200">{brand}</span>
                            </div>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {(result.brand_detection.confidence?.[i] ?? 0) >= 0.01
                                ? `${(result.brand_detection.confidence[i] * 100).toFixed(0)}% match`
                                : ''}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No protected brands detected</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ════ Visual Risk Breakdown ════ */}
            {result.visual_risk && (
              <div className="bg-slate-900/50 border border-slate-700/30 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Layers size={14} className="text-cyan-400" />
                  <p className="text-xs font-semibold text-cyan-400">Risk Score Breakdown</p>
                </div>
                <div className="space-y-2">
                  <ContributionBar
                    label="CNN (MobileNetV3)"
                    value={result.visual_risk.score}
                    weight={60}
                    color="from-cyan-500 to-cyan-400"
                  />
                  <ContributionBar
                    label="OCR Text Analysis"
                    value={result.ocr?.risk_score === 'High' ? 80 : result.ocr?.risk_score === 'Medium' ? 40 : 0}
                    weight={20}
                    color="from-violet-500 to-violet-400"
                  />
                  <ContributionBar
                    label="Brand Detection"
                    value={result.brand_detection?.risk_score === 'High' ? 100 : result.brand_detection?.risk_score === 'Medium' ? 50 : 0}
                    weight={20}
                    color="from-amber-500 to-amber-400"
                  />
                </div>
              </div>
            )}

            {/* ════ Pipeline Steps ════ */}
            <div className="bg-slate-900/50 border border-slate-700/30 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-400 mb-3">AI Analysis Pipeline</p>
              <ul className="space-y-2">
                {[
                  'Image Validation & Preprocessing',
                  'CNN Classification (MobileNetV3)',
                  'Grad-CAM Explainability',
                  'OCR Text Extraction (EasyOCR)',
                  'Brand Logo Detection (ORB)',
                  'Visual Risk Aggregation',
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-2.5 text-xs text-slate-500">
                    <div className="flex items-center justify-center h-5 w-5 rounded-full bg-cyan-500/10 text-[9px] font-bold text-cyan-400">
                      {i + 1}
                    </div>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* ════ Explanation ════ */}
            {result.explanation?.length > 0 && (
              <div className="border-t border-slate-700/30 pt-4">
                <button
                  onClick={() => setShowExplanation(!showExplanation)}
                  className="flex items-center gap-2 text-xs text-cyan-400 hover:text-cyan-300 transition-colors w-full font-medium"
                >
                  {showExplanation ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  {showExplanation ? 'Hide' : 'Show'} Detection Explanation
                </button>

                {showExplanation && (
                  <div className="mt-3 space-y-2 animate-in">
                    {result.explanation.map((item, idx) => {
                      const isRisk = item.toLowerCase().includes('phishing') || item.toLowerCase().includes('risk') || item.toLowerCase().includes('suspicious') || item.toLowerCase().includes('keyword')
                      return (
                        <div key={idx} className="px-3 py-2.5 rounded-xl bg-slate-900/60 border border-slate-700/25 text-xs space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-base leading-none">{isRisk ? '⚠️' : '✅'}</span>
                            <span className="font-semibold text-slate-200">Step {idx + 1}</span>
                          </div>
                          <p className="text-slate-500 pl-7 leading-relaxed">{item}</p>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ════ Scan Again ════ */}
            <button
              onClick={handleScanAgain}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              <RotateCw size={14} />
              Scan Again
            </button>

          </div>
        </div>
      )}
    </div>
  )
}

const ContributionBar = ({ label, value, weight, color }) => (
  <div className="space-y-1">
    <div className="flex items-center justify-between text-[10px]">
      <span className="text-slate-400">{label}</span>
      <span className="text-slate-500 font-mono">Weight: {weight}%</span>
    </div>
    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full bg-gradient-to-r ${color} transition-all duration-700`}
        style={{ width: `${Math.min(100, value)}%` }}
      />
    </div>
  </div>
)

export default VisualScanner
