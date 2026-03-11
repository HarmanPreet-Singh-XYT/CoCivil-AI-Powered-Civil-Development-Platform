"use client";
import { useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { authClient } from '../lib/auth-client.js';

function ResetPasswordForm() {
    const searchParams = useSearchParams();
    const token = searchParams.get('token');

    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    
    // Form State
    const [formData, setFormData] = useState({
        password: '',
        confirmPassword: ''
    });

    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        setError('');
        setSuccessMessage('');
    };

    const validateInputs = () => {
        const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]/;

        if (formData.password.length < 8) {
            setError('Password must be at least 8 chars.');
            return false;
        } else if (!passwordRegex.test(formData.password)) {
            setError('Needs uppercase, lowercase, number, & special char.');
            return false;
        }
        
        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match.');
            return false;
        }

        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!token) {
            setError("Invalid or missing reset token. Please request a new link.");
            return;
        }
        
        if (!validateInputs()) return;
        
        setIsLoading(true);
        setError('');

        try {
            const { error: apiError } = await authClient.resetPassword({
                newPassword: formData.password,
                token: token
            });
            
            if (apiError) {
                setError(apiError.message || 'Failed to reset password. The link might be expired.');
                setIsLoading(false);
                return;
            }
            
            setSuccessMessage("Password reset successfully. Redirecting to login...");
            setTimeout(() => {
                window.location.href = '/login';
            }, 3000);
        } catch (err) {
            console.error(err);
            setError(err.message || 'An unexpected error occurred. Please try again.');
            setIsLoading(false);
        }
    };

    return (
        <div className="layout-container">
            <style>{`
                /* Layout & Media Queries */
                .layout-container {
                    display: flex;
                    width: 100%;
                    min-height: 100vh;
                    background-color: #0A0A0C;
                    font-family: system-ui, -apple-system, sans-serif;
                }
                .hero-section {
                    display: none;
                    flex: 1;
                    position: relative;
                    overflow: hidden;
                    border-right: 1px solid rgba(255,255,255,0.05);
                }
                .form-section {
                    width: 100%;
                    position: relative;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 24px;
                    background-color: #0f0f11;
                }
                .mobile-brand { display: flex; }
                
                @media (min-width: 1024px) {
                    .hero-section { display: block; }
                    .form-section { width: 480px; padding: 48px; }
                    .mobile-brand { display: none; }
                }

                /* Form Elements */
                .input-group {
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .login-label {
                    display: flex;
                    justify-content: space-between;
                    font-size: 13px;
                    font-weight: 500;
                    color: #d6d3d1;
                }
                .login-input {
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    background: rgba(255, 255, 255, 0.03);
                    color: #fff;
                    border-radius: 8px;
                    padding: 14px 16px;
                    font-size: 15px;
                    transition: all 0.2s ease;
                    width: 100%;
                    outline: none;
                }
                .login-input.password-field { padding-right: 48px; }
                .login-input:focus {
                    border-color: #c8a55c;
                    background: rgba(255, 255, 255, 0.05);
                    box-shadow: 0 0 0 1px #c8a55c;
                }
                .login-input.has-error {
                    border-color: #f87171;
                    box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.2);
                }
                
                /* Buttons & Toggles */
                .password-toggle {
                    position: absolute;
                    right: 12px;
                    top: 50%;
                    transform: translateY(-50%);
                    background: none;
                    border: none;
                    color: #a8a29e;
                    cursor: pointer;
                    padding: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: color 0.2s ease;
                }
                .password-toggle:hover { color: #fff; }
                
                .login-btn {
                    background: #c8a55c;
                    color: #111;
                    border: none;
                    font-weight: 600;
                    font-size: 15px;
                    border-radius: 8px;
                    padding: 14px 16px;
                    transition: all 0.2s ease;
                    width: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    cursor: pointer;
                    margin-top: 8px;
                }
                .login-btn:hover:not(:disabled) {
                    background: #dfc07f;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(200, 165, 92, 0.2);
                }
                .login-btn:disabled {
                    opacity: 0.7;
                    cursor: not-allowed;
                }

                /* Aesthetic Classes */
                .auth-card {
                    width: 100%;
                    max-width: 440px;
                    position: relative;
                    z-index: 10;
                    padding: 48px;
                    background: rgba(20, 20, 22, 0.5);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-top: 1px solid rgba(255, 255, 255, 0.15);
                    box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.8);
                    backdrop-filter: blur(24px);
                    -webkit-backdrop-filter: blur(24px);
                    border-radius: 16px;
                }
                .form-bg-grid {
                    position: absolute;
                    inset: 0;
                    background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), 
                                      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
                    background-size: 32px 32px;
                }
                .brand-logo {
                    width: 32px;
                    height: 32px;
                    border-radius: 8px;
                    background: linear-gradient(45deg, #c8a55c, #dfc07f);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 0 15px rgba(200,165,92,0.3);
                    color: #000;
                    font-weight: bold;
                    font-size: 18px;
                    line-height: 1;
                }
                .text-gradient {
                    background: linear-gradient(135deg, #fff 0%, #a8a29e 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .error-alert {
                    padding: 16px;
                    border-radius: 8px;
                    background-color: rgba(248, 113, 113, 0.1);
                    border: 1px solid rgba(248, 113, 113, 0.2);
                    color: #f87171;
                    font-size: 14px;
                    display: flex;
                    gap: 12px;
                    align-items: flex-start;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>

            {/* Visual Left Side - Controlled via CSS Media Queries */}
            <div className="hero-section">
                <div style={{ backgroundImage: 'url(/hero-bg.png)', backgroundSize: 'cover', backgroundPosition: 'center', position: 'absolute', inset: 0, opacity: 0.8 }}></div>
                <div style={{ background: 'linear-gradient(135deg, rgba(10, 10, 12, 0.95) 0%, rgba(10, 10, 12, 0.3) 50%, rgba(10, 10, 12, 0.8) 100%)', position: 'absolute', inset: 0 }}></div>

                <div style={{ position: 'absolute', top: '48px', left: '48px', zIndex: 10, display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div className="brand-logo">C</div>
                    <span style={{ fontSize: '20px', fontWeight: '500', letterSpacing: '0.02em', color: '#fff' }}>CoCivil</span>
                </div>

                <div style={{ position: 'absolute', bottom: '64px', left: '48px', zIndex: 10, maxWidth: '600px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                        <span style={{ height: '2px', width: '32px', backgroundColor: '#c8a55c' }}></span>
                        <span style={{ color: '#dfc07f', fontWeight: '600', letterSpacing: '0.1em', fontSize: '12px', textTransform: 'uppercase' }}>Professional Platform</span>
                    </div>
                    <h2 className="text-gradient" style={{ fontSize: '48px', fontWeight: '300', lineHeight: 1.1, marginBottom: '24px', letterSpacing: '-0em' }}>
                        Intelligent workflows for<br />modern land development.
                    </h2>
                    <p style={{ fontSize: '18px', color: '#a8a29e', fontWeight: '300', lineHeight: 1.6, maxWidth: '500px' }}>
                        Generate massings, calculate financial risk, and extract municipal zoning compliance instantly with CoCivil's due diligence platform.
                    </p>
                </div>
            </div>

            {/* Form Right Side */}
            <div className="form-section">
                <div className="form-bg-grid"></div>

                <div className="mobile-brand" style={{ position: 'absolute', top: '32px', left: '32px', alignItems: 'center', gap: '12px', zIndex: 20 }}>
                    <div className="brand-logo">C</div>
                    <span style={{ fontSize: '20px', fontWeight: '500', letterSpacing: '0.02em', color: '#fff' }}>CoCivil</span>
                </div>

                <div className="auth-card">
                    <div style={{ marginBottom: '40px' }}>
                        <h1 style={{ fontSize: '32px', fontWeight: '600', letterSpacing: '-0.02em', color: '#fff', marginBottom: '8px' }}>
                            Reset Password
                        </h1>
                        <p style={{ fontSize: '15px', color: '#a8a29e', fontWeight: '400' }}>
                            Enter your new password to regain access
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                        {error && (
                            <div className="error-alert">
                                <svg xmlns="http://www.w3.org/2000/svg" style={{ width: '20px', height: '20px', flexShrink: 0, marginTop: '2px' }} viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                <span style={{ lineHeight: 1.5 }}>{error}</span>
                            </div>
                        )}
                        {successMessage && (
                            <div className="error-alert" style={{ backgroundColor: 'rgba(52, 211, 153, 0.1)', borderColor: 'rgba(52, 211, 153, 0.2)', color: '#34d399' }}>
                                <svg xmlns="http://www.w3.org/2000/svg" style={{ width: '20px', height: '20px', flexShrink: 0, marginTop: '2px' }} viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM13.707 8.707a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                <span style={{ lineHeight: 1.5 }}>{successMessage}</span>
                            </div>
                        )}

                        <div className="input-group">
                            <label htmlFor="password" className="login-label">
                                New Password
                            </label>
                            <div style={{ position: 'relative' }}>
                                <input id="password" name="password" type={showPassword ? "text" : "password"} value={formData.password} onChange={handleInputChange} placeholder="••••••••" className="login-input password-field" />
                                <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>
                                    {showPassword ? (
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                                    ) : (
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        <div className="input-group">
                            <label htmlFor="confirmPassword" className="login-label">
                                Confirm New Password
                            </label>
                            <input id="confirmPassword" name="confirmPassword" type="password" value={formData.confirmPassword} onChange={handleInputChange} placeholder="••••••••" className="login-input" />
                        </div>

                        <button type="submit" disabled={isLoading} className="login-btn">
                            {isLoading ? (
                                <svg style={{ width: '20px', height: '20px', color: '#111', animation: 'spin 1s linear infinite' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            ) : (
                                <span>Reset Password</span>
                            )}
                        </button>
                    </form>

                    <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.08)', textAlign: 'center', fontSize: '14px', color: '#a8a29e' }}>
                        Remember your password? 
                        <a href="/login" style={{ color: '#fff', fontWeight: '500', marginLeft: '4px', textDecoration: 'none' }}>
                            Sign in
                        </a>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense fallback={<div style={{ width: '100%', height: '100vh', backgroundColor: '#0A0A0C' }}></div>}>
            <ResetPasswordForm />
        </Suspense>
    );
}
