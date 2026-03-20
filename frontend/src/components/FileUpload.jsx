import { useState, useRef, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

export default function FileUpload({ onUploadComplete, onUploadStart }) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) processFile(droppedFile);
  }, []);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) processFile(selectedFile);
  };

  const processFile = (f) => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['txt', 'edi'].includes(ext)) {
      setError('Only .txt and .edi files are accepted');
      return;
    }
    setFile(f);
    setError(null);
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  const uploadFile = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(10);
    setError(null);
    onUploadStart && onUploadStart();

    try {
      setProgress(30);
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      setProgress(70);

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await response.json();
      setProgress(100);

      setTimeout(() => {
        onUploadComplete && onUploadComplete(data);
        setUploading(false);
      }, 300);
    } catch (err) {
      setError(err.message || 'Failed to upload file');
      setUploading(false);
      setProgress(0);
    }
  };

  const removeFile = () => {
    setFile(null);
    setProgress(0);
    setError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon">📂</span>
          File Upload
        </div>
        {file && (
          <span className="badge badge-info">Ready</span>
        )}
      </div>
      <div className="panel-body">
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          id="upload-zone"
        >
          <span className="upload-icon">⬆️</span>
          <div className="upload-text">
            <h3>Drop your EDI file here</h3>
            <p>
              or <span className="highlight">click to browse</span>
              <br />
              Supports <strong>.txt</strong> and <strong>.edi</strong> files
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".txt,.edi"
            className="upload-input"
            onChange={handleFileSelect}
            id="file-input"
          />
        </div>

        {error && (
          <div className="tree-error-detail" style={{ marginTop: '12px', marginLeft: 0 }}>
            <span className="tree-error-message">⚠️ {error}</span>
          </div>
        )}

        {file && (
          <div className="file-info">
            <span className="file-info-icon">📄</span>
            <div className="file-info-details">
              <div className="file-info-name">{file.name}</div>
              <div className="file-info-meta">{formatSize(file.size)}</div>
            </div>
            <button
              className="file-info-remove"
              onClick={(e) => { e.stopPropagation(); removeFile(); }}
              title="Remove file"
            >
              ✕
            </button>
          </div>
        )}

        {uploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="progress-text">
              <span>Parsing EDI file...</span>
              <span>{progress}%</span>
            </div>
          </div>
        )}

        {file && !uploading && (
          <button
            className="btn btn-primary"
            onClick={uploadFile}
            style={{ marginTop: '16px', width: '100%', justifyContent: 'center' }}
            id="upload-btn"
          >
            🚀 Parse & Analyze
          </button>
        )}
      </div>
    </div>
  );
}
