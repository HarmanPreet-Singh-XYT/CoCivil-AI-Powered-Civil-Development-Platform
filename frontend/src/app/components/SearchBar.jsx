import { useState, useRef, useCallback, useEffect } from 'react';

function formatAddress(result) {
    const addr = result.address || {};
    const parts = [];
    if (addr.house_number) parts.push(addr.house_number);
    if (addr.road) parts.push(addr.road);
    if (parts.length === 0) return result.display_name.split(',')[0];
    const city = addr.city || addr.town || addr.village || '';
    const province = addr.state || '';
    const postal = addr.postcode || '';
    let formatted = parts.join(' ');
    if (city) formatted += `, ${city}`;
    if (province) formatted += `, ${province}`;
    if (postal) formatted += ` ${postal}`;
    return formatted;
}

export default function SearchBar({ onLocationSelected }) {
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const debounceRef = useRef(null);
    const barRef = useRef(null);

    const geocode = useCallback(async (q) => {
        try {
            const url = `https://nominatim.openstreetmap.org/search?` +
                `q=${encodeURIComponent(q + ' Toronto Canada')}&` +
                `format=json&addressdetails=1&limit=6&countrycodes=ca`;

            const res = await fetch(url, {
                headers: { 'Accept-Language': 'en' },
            });
            const results = await res.json();

            if (results.length === 0) {
                setSuggestions([{ noResults: true }]);
            } else {
                setSuggestions(results);
            }
            setShowSuggestions(true);
        } catch (err) {
            console.error('Geocoding error:', err);
        }
    }, []);

    const handleInput = useCallback((e) => {
        const val = e.target.value;
        setQuery(val);
        clearTimeout(debounceRef.current);
        if (val.trim().length < 3) {
            setShowSuggestions(false);
            return;
        }
        debounceRef.current = setTimeout(() => geocode(val.trim()), 350);
    }, [geocode]);

    const handleSuggestionClick = useCallback((result) => {
        setQuery(formatAddress(result));
        setShowSuggestions(false);
        onLocationSelected({
            lng: parseFloat(result.lon),
            lat: parseFloat(result.lat),
            address: result.display_name,
            shortAddress: formatAddress(result),
        });
    }, [onLocationSelected]);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Escape') {
            setShowSuggestions(false);
            e.target.blur();
        }
        if (e.key === 'Enter' && suggestions.length > 0 && !suggestions[0].noResults) {
            handleSuggestionClick(suggestions[0]);
        }
    }, [handleSuggestionClick, suggestions]);

    // Close suggestions on outside click
    useEffect(() => {
        const handleClick = (e) => {
            if (barRef.current && !barRef.current.contains(e.target)) {
                setShowSuggestions(false);
            }
        };
        document.addEventListener('click', handleClick);
        return () => document.removeEventListener('click', handleClick);
    }, []);

    return (
        <div id="search-container">
            <div id="search-bar" ref={barRef}>
                <svg id="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input
                    type="text"
                    id="search-input"
                    placeholder="Search address, PIN, or location..."
                    autoComplete="off"
                    value={query}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                />
                <div id="search-suggestions" className={showSuggestions ? 'visible' : ''}>
                    {suggestions.map((result, idx) =>
                        result.noResults ? (
                            <div key="no-results" className="suggestion-item" style={{ pointerEvents: 'none', opacity: 0.5 }}>
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                                </svg>
                                <div className="suggestion-text">
                                    <div className="suggestion-main">No results found</div>
                                    <div className="suggestion-sub">Try a different address or location</div>
                                </div>
                            </div>
                        ) : (
                            <div
                                key={idx}
                                className="suggestion-item"
                                onClick={() => handleSuggestionClick(result)}
                            >
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                                    <circle cx="12" cy="10" r="3" />
                                </svg>
                                <div className="suggestion-text">
                                    <div className="suggestion-main">{formatAddress(result)}</div>
                                    <div className="suggestion-sub">{result.display_name}</div>
                                </div>
                            </div>
                        )
                    )}
                </div>
            </div>
        </div>
    );
}
