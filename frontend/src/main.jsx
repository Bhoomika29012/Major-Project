import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './utils/AuthContext'
import { ProtectedLayout, PublicLayout } from './App'
import Dashboard from './pages/Dashboard'
import URLScannerPage from './pages/URLScannerPage'
import SMSAnalyzerPage from './pages/SMSAnalyzerPage'
import QRScannerPage from './pages/QRScannerPage'
import VisualScannerPage from './pages/VisualScannerPage'
import ScanHistory from './pages/ScanHistory'
import Profile from './pages/Profile'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <BrowserRouter>
            <AuthProvider>
                <Routes>
                    {/* Public routes */}
                    <Route path="/login" element={<PublicLayout><LoginPage /></PublicLayout>} />
                    <Route path="/register" element={<PublicLayout><RegisterPage /></PublicLayout>} />

                    {/* Protected routes */}
                    <Route element={<ProtectedLayout />}>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/url-scanner" element={<URLScannerPage />} />
                        <Route path="/sms-scanner" element={<SMSAnalyzerPage />} />
                        <Route path="/qr-scanner" element={<QRScannerPage />} />
                        <Route path="/visual-scanner" element={<VisualScannerPage />} />
                        <Route path="/history" element={<ScanHistory />} />
                        <Route path="/profile" element={<Profile />} />
                    </Route>

                    {/* Catch all - redirect to home */}
                    <Route path="*" element={<div className="min-h-screen flex items-center justify-center bg-[#020617]"><p className="text-slate-500">Redirecting...</p></div>} />
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    </React.StrictMode>,
)
