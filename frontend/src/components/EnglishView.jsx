import React from 'react';

export default function EnglishView({ text }) {
  if (!text) {
    return (
      <div className="panel" style={{ flex: 1 }}>
        <div className="panel-header">
          <div className="panel-title">
            <span className="panel-title-icon">📝</span>
            Plain English Summary
          </div>
        </div>
        <div className="panel-body">
          <div className="tree-empty">
            <span className="tree-empty-icon">🔍</span>
            <h3>No translation available</h3>
            <p>Upload a file to generate an English summary.</p>
          </div>
        </div>
      </div>
    );
  }

  // Very basic Markdown to React element parser
  const formatText = (content) => {
    return content.split('\n').map((line, idx) => {
      // Headers
      if (line.startsWith('# ')) {
        return <h2 key={idx} style={{ marginTop: '20px', marginBottom: '10px', color: 'var(--text-main)' }}>{line.substring(2)}</h2>;
      }
      if (line.startsWith('## ')) {
        return <h3 key={idx} style={{ marginTop: '16px', marginBottom: '8px', color: 'var(--primary)' }}>{line.substring(3)}</h3>;
      }
      
      // Parse bold **text** inline
      const parts = line.split(/(\*\*.*?\*\*)/g);
      const formattedLine = parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} style={{ color: 'var(--text-main)' }}>{part.substring(2, part.length - 2)}</strong>;
        }
        return part;
      });

      // Handle indentation for lists
      const leadingSpaces = line.search(/\S|$/);
      const isListItem = line.trim().startsWith('-') || line.trim().startsWith('*');
      
      if (leadingSpaces > 0 || isListItem) {
        return (
          <div key={idx} style={{ marginLeft: `${(leadingSpaces / 2) * 20}px`, padding: '4px 0', color: 'var(--text-muted)' }}>
             {formattedLine}
          </div>
        );
      }
      
      return <p key={idx} style={{ margin: '8px 0', color: 'var(--text-muted)' }}>{formattedLine}</p>;
    });
  };

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon">📝</span>
          Plain English Summary
        </div>
      </div>
      <div className="panel-body" style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
        {formatText(text)}
      </div>
    </div>
  );
}
