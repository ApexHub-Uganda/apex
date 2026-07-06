import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Apex Hub render error:', error, info);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="min-vh-100 d-flex align-items-center justify-content-center p-4 bg-light">
        <div className="apex-card p-4 p-md-5 text-center" style={{ maxWidth: 520 }}>
          <h5 className="fw-bold mb-2">Something went wrong</h5>
          <p className="text-muted small mb-3">
            The page failed to load. Try a hard refresh (Ctrl+Shift+R). If this keeps happening, restart the frontend dev server.
          </p>
          <pre className="text-start small text-danger bg-danger-subtle p-3 rounded mb-3" style={{ whiteSpace: 'pre-wrap' }}>
            {error?.message || String(error)}
          </pre>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;