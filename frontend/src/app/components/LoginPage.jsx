import { useState, useCallback } from 'react';
import { login, register } from '../api.js';

export default function LoginPage({ onAuth }) {
    const [isRegister, setIsRegister] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [orgName, setOrgName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = useCallback(async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            let data;
            if (isRegister) {
                data = await register({ email, password, name, organization_name: orgName });
            } else {
                data = await login({ email, password });
            }
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            onAuth(data);
        } catch (err) {
            setError(err.message || 'Authentication failed');
        } finally {
            setLoading(false);
        }
    }, [isRegister, email, password, name, orgName, onAuth]);

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0a0a0f',
        }}>
            <form onSubmit={handleSubmit} style={{
                background: '#16161e',
                borderRadius: 12,
                padding: '2.5rem',
                width: 380,
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                border: '1px solid rgba(255,255,255,0.06)',
            }}>
                <h2 style={{ color: '#fff', margin: 0, textAlign: 'center' }}>
                    {isRegister ? 'Create Account' : 'Sign In'}
                </h2>

                {error && (
                    <div style={{ color: '#f87171', fontSize: 14, textAlign: 'center' }}>{error}</div>
                )}

                {isRegister && (
                    <>
                        <input
                            type="text"
                            placeholder="Full Name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            style={inputStyle}
                        />
                        <input
                            type="text"
                            placeholder="Organization Name"
                            value={orgName}
                            onChange={(e) => setOrgName(e.target.value)}
                            required
                            style={inputStyle}
                        />
                    </>
                )}

                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    style={inputStyle}
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    style={inputStyle}
                />

                <button
                    type="submit"
                    disabled={loading}
                    style={{
                        padding: '0.75rem',
                        borderRadius: 8,
                        border: 'none',
                        background: '#6366f1',
                        color: '#fff',
                        fontWeight: 600,
                        fontSize: 15,
                        cursor: loading ? 'wait' : 'pointer',
                        opacity: loading ? 0.7 : 1,
                    }}
                >
                    {loading ? 'Please wait...' : isRegister ? 'Register' : 'Sign In'}
                </button>

                <button
                    type="button"
                    onClick={() => { setIsRegister(!isRegister); setError(''); }}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: '#818cf8',
                        cursor: 'pointer',
                        fontSize: 14,
                    }}
                >
                    {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
                </button>
            </form>
        </div>
    );
}

const inputStyle = {
    padding: '0.7rem 0.9rem',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.1)',
    background: '#1e1e2a',
    color: '#fff',
    fontSize: 15,
    outline: 'none',
};
