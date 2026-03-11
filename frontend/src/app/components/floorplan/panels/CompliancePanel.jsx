import { useState } from 'react';

function SeverityIcon({ severity }) {
  if (severity === 'error' || severity === 'blocker') {
    return <span className="compliance-icon compliance-icon--error">&times;</span>;
  }
  if (severity === 'warning') {
    return <span className="compliance-icon compliance-icon--warning">!</span>;
  }
  return <span className="compliance-icon compliance-icon--pass">&#10003;</span>;
}

export default function CompliancePanel({
  complianceResult,
  selectedElementId,
  onRuleClick,
  loading,
  onClose,
}) {
  const [expandedRule, setExpandedRule] = useState(null);

  if (!complianceResult) {
    return (
      <div className="floorplan-compliance-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
          <h3 style={{ margin: 0 }}>OBC Compliance</h3>
          {onClose && <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: 'var(--text-secondary)' }}>✕</button>}
        </div>
        <div className="compliance-empty-state">
          Upload a DXF floor plan to check interior compliance
        </div>
      </div>
    );
  }

  const rules = complianceResult.rules || [];
  const errors = rules.filter(
    (r) => !r.compliant && (r.severity === 'error' || r.severity === 'blocker')
  );
  const warnings = rules.filter((r) => r.severity === 'warning' && r.note);
  const passed = rules.filter((r) => r.compliant && !(r.severity === 'warning' && r.note));

  const allPass = errors.length === 0 && warnings.length === 0;

  // Group rules by element_id
  const byElement = {};
  for (const rule of rules) {
    const eid = rule.element_id || '_global';
    if (!byElement[eid]) byElement[eid] = [];
    byElement[eid].push(rule);
  }

  // Load-bearing warnings
  const lbWarnings = complianceResult.load_bearing_warnings || [];

  return (
    <div className="floorplan-compliance-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
        <h3 style={{ margin: 0 }}>
          OBC Compliance
          {loading && <span className="compliance-loading-dot" />}
        </h3>
        {onClose && <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', color: 'var(--text-secondary)' }}>✕</button>}
      </div>

      {/* Overall status */}
      <div className={`compliance-status ${allPass ? 'pass' : 'fail'}`}>
        {allPass ? 'All checks pass' : 'Issues found'}
      </div>

      {/* Summary bar */}
      <div className="compliance-summary-bar">
        {errors.length > 0 && (
          <span className="compliance-summary-chip compliance-summary-chip--error">
            {errors.length} error{errors.length !== 1 ? 's' : ''}
          </span>
        )}
        {warnings.length > 0 && (
          <span className="compliance-summary-chip compliance-summary-chip--warning">
            {warnings.length} warning{warnings.length !== 1 ? 's' : ''}
          </span>
        )}
        <span className="compliance-summary-chip compliance-summary-chip--pass">
          {passed.length} passed
        </span>
      </div>

      {/* Load-bearing warnings */}
      {lbWarnings.length > 0 && (
        <div className="compliance-lb-banner">
          <strong>Load-bearing warnings</strong>
          {lbWarnings.map((w, i) => (
            <div key={i} className="compliance-lb-item">{w}</div>
          ))}
        </div>
      )}

      {/* Rule list grouped by element */}
      <div className="compliance-rules-list">
        {Object.entries(byElement).map(([elementId, elementRules]) => (
          <div
            key={elementId}
            className={`compliance-element-group ${
              elementId === selectedElementId ? 'compliance-element-group--selected' : ''
            }`}
          >
            <div className="compliance-element-header">
              {elementId === '_global' ? 'General' : elementId}
            </div>
            {elementRules.map((rule, idx) => {
              const ruleKey = `${elementId}_${idx}`;
              const isExpanded = expandedRule === ruleKey;
              return (
                <div
                  key={ruleKey}
                  className={`compliance-rule-item compliance-rule-item--${rule.severity}`}
                  onClick={() => {
                    if (rule.element_id) onRuleClick?.(rule.element_id);
                    setExpandedRule(isExpanded ? null : ruleKey);
                  }}
                >
                  <div className="compliance-rule-header">
                    <SeverityIcon severity={rule.severity} />
                    <span className="compliance-rule-name">
                      {rule.parameter || rule.rule}
                    </span>
                    {rule.obc_section && (
                      <span className="compliance-rule-section">
                        {rule.obc_section}
                      </span>
                    )}
                  </div>
                  {isExpanded && (
                    <div className="compliance-rule-detail">
                      {rule.required != null && (
                        <div className="compliance-rule-values">
                          <span>Required: {rule.required}{rule.unit ? ` ${rule.unit}` : ''}</span>
                          <span>Actual: {rule.actual}{rule.unit ? ` ${rule.unit}` : ''}</span>
                        </div>
                      )}
                      {rule.description && (
                        <div className="compliance-rule-description">{rule.description}</div>
                      )}
                      {rule.note && (
                        <div className="compliance-rule-note">{rule.note}</div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
