const STATUS_COLORS = {
  pass: '#4ade80',
  warning: '#fbbf24',
  fail: '#f87171',
  info: '#60a5fa',
};

export default function InfrastructureCompliancePanel({ results, onClose }) {
  if (!results?.rules?.length) {
    return (
      <div className="infra-compliance-panel">
        <div className="infra-compliance-header">
          <span>Compliance</span>
          <button onClick={onClose}>x</button>
        </div>
        <div style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)' }}>
          No compliance data available. Edit the design to trigger a check.
        </div>
      </div>
    );
  }

  const passCount = results.rules.filter((r) => r.status === 'pass').length;
  const totalCount = results.rules.length;

  return (
    <div className="infra-compliance-panel">
      <div className="infra-compliance-header">
        <span>Compliance ({passCount}/{totalCount})</span>
        <button onClick={onClose}>x</button>
      </div>
      {results.rules.map((rule, i) => (
        <div key={i} className="infra-compliance-item">
          <div
            className="infra-compliance-status"
            style={{ backgroundColor: STATUS_COLORS[rule.status] || STATUS_COLORS.info }}
          />
          <div>
            <div style={{ color: 'var(--text-primary)', marginBottom: 2 }}>{rule.name}</div>
            {rule.detail && (
              <div style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)' }}>
                {rule.detail}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
