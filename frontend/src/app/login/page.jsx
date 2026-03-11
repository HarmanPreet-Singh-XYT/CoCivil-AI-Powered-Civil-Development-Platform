"use client";
import { useState } from 'react';
import { authClient } from '../lib/auth-client.js';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [isLogin, setIsLogin] = useState(true);

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (isLogin) {
                await authClient.signIn.email({ email, password });
            } else {
                await authClient.signUp.email({ email, password, name });
            }
            window.location.href = '/';
        } catch (error) {
            console.error(error);
            alert(error.message || 'Authentication failed');
        }
    };

    return (
        <div style={{ padding: '2rem', maxWidth: '400px', margin: '0 auto' }}>
            <h2>{isLogin ? 'Login' : 'Sign Up'}</h2>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {!isLogin && (
                    <input
                        type="text"
                        placeholder="Name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        style={{ padding: '0.5rem' }}
                    />
                )}
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    style={{ padding: '0.5rem' }}
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    style={{ padding: '0.5rem' }}
                />
                <button type="submit" style={{ padding: '0.5rem', background: '#0070f3', color: 'white' }}>
                    {isLogin ? 'Log In' : 'Sign Up'}
                </button>
            </form>
            <button
                onClick={() => setIsLogin(!isLogin)}
                style={{ marginTop: '1rem', background: 'none', border: 'none', color: '#0070f3', cursor: 'pointer' }}
            >
                {isLogin ? 'Need an account? Sign up' : 'Already have an account? Log in'}
            </button>
        </div>
    );
}
