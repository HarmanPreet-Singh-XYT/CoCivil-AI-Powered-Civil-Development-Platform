import React from 'react';
import '../styles/settings-modal.css';

export default function DashboardModal({ isOpen, onClose }) {
    if (!isOpen) return null;

    return (
        <div className="settings-overlay backdrop-blur-xl" onClick={onClose}>
            <div className="settings-modal backdrop-blur-xl" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px' }}>
                <div className="settings-header">
                    <h2>Dashboard & Billing</h2>
                    <button className="settings-close" onClick={onClose} title="Close Dashboard">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                    </button>
                </div>
                
                <div className="settings-content">
                    {/* Subscription Plan */}
                    <div className="settings-section">
                        <h3>Current Plan</h3>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-accent)' }}>
                            <div>
                                <h4 style={{ margin: 0, color: 'var(--accent)', fontSize: '18px' }}>Pro Plan</h4>
                                <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '12px' }}>$49.00 / month, renews on Aug 1st</p>
                            </div>
                            <button className="btn-secondary" style={{ fontSize: '12px', padding: '6px 12px' }}>Manage Plan</button>
                        </div>
                    </div>

                    {/* Usage Statistics */}
                    <div className="settings-section">
                        <h3>Usage & Credits</h3>
                        <div style={{ display: 'flex', gap: '16px' }}>
                            <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>API Credits Used</div>
                                <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--text-primary)' }}>1,248 <span style={{fontSize:'12px', color:'var(--text-muted)', fontWeight:'normal'}}>/ 5000</span></div>
                                <div style={{ marginTop: '8px', width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                                    <div style={{ width: '25%', height: '100%', background: 'var(--accent)' }}></div>
                                </div>
                            </div>
                            <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Active Projects</div>
                                <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--text-primary)' }}>12 <span style={{fontSize:'12px', color:'var(--text-muted)', fontWeight:'normal'}}>/ unlmt.</span></div>
                                <div style={{ marginTop: '8px', width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                                    <div style={{ width: '100%', height: '100%', background: 'var(--success)' }}></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Recent Invoices */}
                    <div className="settings-section">
                        <h3>Recent Invoices</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {[
                                { date: 'Jul 1, 2026', amount: '$49.00', status: 'Paid' },
                                { date: 'Jun 1, 2026', amount: '$49.00', status: 'Paid' },
                                { date: 'May 1, 2026', amount: '$49.00', status: 'Paid' },
                            ].map((invoice, i) => (
                                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(0,0,0,0.1)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                                    <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{invoice.date}</span>
                                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                                        <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-primary)' }}>{invoice.amount}</span>
                                        <span style={{ fontSize: '11px', background: 'rgba(52, 211, 153, 0.1)', color: 'var(--success)', padding: '2px 6px', borderRadius: '4px' }}>{invoice.status}</span>
                                        <button style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '12px' }}>↓</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="settings-footer">
                    <button className="btn-secondary" onClick={onClose}>Close</button>
                </div>
            </div>
        </div>
    );
}
