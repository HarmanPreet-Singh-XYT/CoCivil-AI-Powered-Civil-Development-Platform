import React, { useState } from 'react';
import '../styles/settings-modal.css';

export default function SettingsModal({ isOpen, onClose, user }) {
    if (!isOpen) return null;

    const [darkMode, setDarkMode] = useState(true);
    const [notifications, setNotifications] = useState(true);

    return (
        <div className="settings-overlay backdrop-blur-xl" onClick={onClose}>
            <div className="settings-modal backdrop-blur-xl" onClick={e => e.stopPropagation()}>
                <div className="settings-header">
                    <h2>Account Settings</h2>
                    <button className="settings-close" onClick={onClose} title="Close Settings">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                    </button>
                </div>
                <div className="settings-content">
                    <div className="settings-section">
                        <h3>Profile Information</h3>
                        <div className="form-group">
                            <label>Name</label>
                            <input type="text" value={user?.name || ''} readOnly />
                        </div>
                        <div className="form-group">
                            <label>Email</label>
                            <input type="email" value={user?.email || ''} readOnly />
                        </div>
                    </div>
                    <div className="settings-section">
                        <h3>Preferences</h3>
                        <div className="form-group toggle-group" onClick={() => setDarkMode(!darkMode)}>
                            <label>Dark Mode</label>
                            <div className={`toggle ${darkMode ? 'active' : ''}`}></div>
                        </div>
                        <div className="form-group toggle-group" onClick={() => setNotifications(!notifications)}>
                            <label>Email Notifications</label>
                            <div className={`toggle ${notifications ? 'active' : ''}`}></div>
                        </div>
                    </div>
                </div>
                <div className="settings-footer">
                    <button className="btn-secondary" onClick={onClose}>Cancel</button>
                    <button className="btn-primary" onClick={onClose}>Save Changes</button>
                </div>
            </div>
        </div>
    );
}
