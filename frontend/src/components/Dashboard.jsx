import { useState, useCallback } from 'react';
import FileUpload from './FileUpload';
import DataTree from './DataTree';
import ChatPanel from './ChatPanel';
import EnglishView from './EnglishView';

const API_BASE = 'http://localhost:8000';

export default function Dashboard() {
  const [parsedData, setParsedData] = useState(null);
  const [stats, setStats] = useState(null);
  const [chatContext, setChatContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('tree');
  const [englishText, setEnglishText] = useState(null);

  const handleUploadStart = useCallback(() => {
    setLoading(true);
  }, []);

  const handleUploadComplete = useCallback((data) => {
    setParsedData(data.parsed);
    setStats(data.stats);
    setChatContext(data);
    setEnglishText(null);
    setViewMode('tree');
    setLoading(false);
  }, []);

  const handleToggleView = useCallback(async (mode) => {
    setViewMode(mode);
    if (mode === 'english' && !englishText && parsedData) {
      try {
        const response = await fetch(`${API_BASE}/api/translate`);
        if (!response.ok) throw new Error('Translation failed');
        const data = await response.json();
        setEnglishText(data.text);
      } catch (err) {
        console.error('Translation error:', err);
      }
    }
  }, [englishText, parsedData]);

  const handleFix = useCallback(async (path, field, suggestedFix) => {
    try {
      const response = await fetch(`${API_BASE}/api/fix`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path,
          field,
          value: suggestedFix.value,
        }),
      });

      if (!response.ok) throw new Error('Fix failed');

      const data = await response.json();
      setParsedData(data.parsed);
      setStats(data.stats);
      setChatContext(data);
    } catch (err) {
      console.error('Fix error:', err);
    }
  }, []);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="app-logo">
          <div className="app-logo-icon">⚡</div>
          <div>
            <h1>EDI Dashboard</h1>
            <span>HIPAA File Parser & Validator</span>
          </div>
        </div>
        <div className="header-badges">
          <span className="badge badge-success">● Online</span>
          <span className="badge badge-info">v1.0</span>
        </div>
      </header>

      {/* Dashboard Grid */}
      <main className="dashboard">
        {/* Left Panel — Upload */}
        <div className="dashboard-left">
          <FileUpload
            onUploadStart={handleUploadStart}
            onUploadComplete={handleUploadComplete}
          />
          <ChatPanel context={chatContext} />
        </div>

        {/* Right Panel — Tree or English */}
        <div className="dashboard-right" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div className="view-toggles" style={{ display: 'flex', gap: '8px' }}>
            <button 
              className="tree-fix-btn"
              style={{ padding: '8px 16px', fontSize: '14px', borderRadius: '4px', cursor: 'pointer', border: '1px solid var(--border)', backgroundColor: viewMode === 'tree' ? 'var(--primary)' : 'var(--bg-card)', color: viewMode === 'tree' ? '#fff' : 'var(--text-main)' }}
              onClick={() => handleToggleView('tree')}
            >
              🌳 Technical Tree
            </button>
            <button 
              className="tree-fix-btn"
              style={{ padding: '8px 16px', fontSize: '14px', borderRadius: '4px', cursor: 'pointer', border: '1px solid var(--border)', backgroundColor: viewMode === 'english' ? 'var(--primary)' : 'var(--bg-card)', color: viewMode === 'english' ? '#fff' : 'var(--text-main)' }}
              onClick={() => handleToggleView('english')}
            >
              📝 Plain English
            </button>
          </div>

          {viewMode === 'tree' ? (
            <DataTree
              data={parsedData}
              stats={stats}
              onFix={handleFix}
            />
          ) : (
            <EnglishView text={englishText} />
          )}
        </div>
      </main>
    </div>
  );
}
