import { useState, useCallback } from 'react';

function TreeNode({ name, data, path = '', onFix }) {
  const [expanded, setExpanded] = useState(false);

  const isObject = data !== null && typeof data === 'object' && !Array.isArray(data);
  const isArray = Array.isArray(data);
  const hasChildren = isObject || isArray;
  const hasError = isObject && data._errors && data._errors.length > 0;

  const currentPath = path ? `${path}.${name}` : name;

  const toggleExpand = useCallback(() => {
    if (hasChildren) setExpanded((prev) => !prev);
  }, [hasChildren]);

  const getIcon = () => {
    if (hasError) return '🔴';
    if (isArray) return '📋';
    if (isObject) return expanded ? '📂' : '📁';
    return '📄';
  };

  const renderValue = () => {
    if (hasChildren) {
      const count = isArray ? data.length : Object.keys(data).filter(k => k !== '_errors').length;
      return `(${count} ${isArray ? 'items' : 'fields'})`;
    }
    if (data === null || data === undefined) return 'null';
    if (typeof data === 'boolean') return data ? 'true' : 'false';
    const str = String(data);
    return str.length > 60 ? str.substring(0, 60) + '…' : str;
  };

  // Get children, excluding internal _errors key
  const getChildren = () => {
    if (isArray) {
      return data.map((item, idx) => ({ key: `[${idx}]`, value: item }));
    }
    if (isObject) {
      return Object.entries(data)
        .filter(([k]) => k !== '_errors')
        .map(([k, v]) => ({ key: k, value: v }));
    }
    return [];
  };

  return (
    <div className="tree-node">
      <div
        className={`tree-node-header ${hasError ? 'has-error' : ''}`}
        onClick={toggleExpand}
      >
        {hasChildren && (
          <span className={`tree-node-toggle ${expanded ? 'expanded' : ''}`}>
            ▶
          </span>
        )}
        {!hasChildren && <span style={{ width: 16 }} />}

        <span className="tree-node-icon">{getIcon()}</span>
        <span className="tree-node-label">{name}</span>
        <span className="tree-node-value">{renderValue()}</span>

        {hasError && (
          <span className="tree-error-badge">
            ⚠ {data._errors.length} error{data._errors.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Error details */}
      {hasError && expanded && data._errors.map((err, idx) => (
        <div className="tree-error-detail" key={idx}>
          <span className="tree-error-message">
            ❌ {err.message}
          </span>
          {err.suggested_fix && (
            <button
              className="tree-fix-btn"
              onClick={(e) => {
                e.stopPropagation();
                onFix && onFix(currentPath, err.field, err.suggested_fix);
              }}
            >
              ✅ Accept Fix
            </button>
          )}
        </div>
      ))}

      {/* Children */}
      {hasChildren && expanded && (
        <div className="tree-node-children">
          {getChildren().map(({ key, value }) => (
            <TreeNode
              key={key}
              name={key}
              data={value}
              path={currentPath}
              onFix={onFix}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DataTree({ data, stats, onFix }) {
  if (!data) {
    return (
      <div className="panel" style={{ flex: 1 }}>
        <div className="panel-header">
          <div className="panel-title">
            <span className="panel-title-icon">🌳</span>
            Parsed Data
          </div>
        </div>
        <div className="panel-body">
          <div className="tree-empty">
            <span className="tree-empty-icon">🔍</span>
            <h3>No data yet</h3>
            <p>Upload an EDI file to see parsed data here</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel" style={{ flex: 1 }}>
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon">🌳</span>
          Parsed Data
        </div>
        {stats && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <span className="badge badge-info">{stats.edi_type}</span>
            {stats.error_count > 0 ? (
              <span className="badge badge-error">{stats.error_count} errors</span>
            ) : (
              <span className="badge badge-success">Valid</span>
            )}
          </div>
        )}
      </div>

      {stats && (
        <div className="stats-bar">
          <div className="stat-item">
            <div className="stat-value">{stats.total_segments || 0}</div>
            <div className="stat-label">Segments</div>
          </div>
          <div className="stat-item">
            <div className="stat-value success">{stats.valid_count || 0}</div>
            <div className="stat-label">Valid</div>
          </div>
          <div className="stat-item">
            <div className="stat-value errors">{stats.error_count || 0}</div>
            <div className="stat-label">Errors</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{stats.edi_type || '—'}</div>
            <div className="stat-label">Type</div>
          </div>
        </div>
      )}

      <div className="panel-body tree-container">
        {Object.entries(data).map(([key, value]) => (
          <TreeNode key={key} name={key} data={value} onFix={onFix} />
        ))}
      </div>
    </div>
  );
}
