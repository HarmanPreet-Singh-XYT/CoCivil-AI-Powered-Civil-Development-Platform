export default function ContractorCards({ contractors }) {
    if (!contractors?.length) return null;

    return (
        <div className="contractor-cards-row">
            {contractors.map((c, i) => (
                <div key={i} className="contractor-card">
                    <div className="contractor-card-name">{c.name}</div>
                    <div className="contractor-card-meta">
                        {c.rating != null && (
                            <span>&#9733; {c.rating}{c.review_count != null ? ` (${c.review_count} reviews)` : ''}</span>
                        )}
                        {c.phone && <span>{c.phone}</span>}
                    </div>
                    {c.website && (
                        <a
                            className="contractor-card-link"
                            href={c.website}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            {new URL(c.website).hostname}
                        </a>
                    )}
                    {c.trade && <span className="contractor-card-trade">{c.trade}</span>}
                </div>
            ))}
        </div>
    );
}
