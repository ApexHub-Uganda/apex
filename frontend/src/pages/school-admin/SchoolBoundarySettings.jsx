import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCrosshair, FiMapPin, FiSave, FiTrash2 } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SchoolBoundaryMap from '../../components/SchoolBoundaryMap';
import { schoolGeofenceService } from '../../services/moduleService';
import { formatAccuracy, getCurrentPosition } from '../../utils/geolocation';
import { extractApiError, notify } from '../../utils/notify';
import { useAuth } from '../../hooks/useAuth';
import { ApexLoader } from '../../components/ApexLoader';

/**
 * School admin: define campus polygon (min 4 GPS corners) on free OpenStreetMap.
 */
export function SchoolBoundarySettings() {
  const { isSchoolAdmin, isSuperAdmin } = useAuth();
  const canManage = Boolean(isSchoolAdmin || isSuperAdmin);
  const queryClient = useQueryClient();
  const [vertices, setVertices] = useState([]);
  const [bufferMeters, setBufferMeters] = useState(25);
  const [isEnabled, setIsEnabled] = useState(false);
  const [name, setName] = useState('Main campus');
  const [capturing, setCapturing] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['school-geofence'],
    queryFn: () => schoolGeofenceService.get(),
    enabled: canManage,
  });

  useEffect(() => {
    if (!data) return;
    setVertices(data.vertices || []);
    setBufferMeters(data.buffer_meters ?? 25);
    setIsEnabled(Boolean(data.is_enabled));
    setName(data.name || 'Main campus');
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => schoolGeofenceService.save({
      vertices,
      buffer_meters: Number(bufferMeters) || 25,
      is_enabled: isEnabled,
      name: name || 'Main campus',
    }),
    onSuccess: () => {
      notify.success('School boundary saved.');
      queryClient.invalidateQueries({ queryKey: ['school-geofence'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to save boundary.')),
  });

  const addPointFromMap = (pt) => {
    if (!canManage) return;
    if (vertices.length >= 64) {
      notify.warning('Maximum 64 boundary points.');
      return;
    }
    setVertices((prev) => [
      ...prev,
      {
        lat: Number(pt.lat.toFixed(7)),
        lng: Number(pt.lng.toFixed(7)),
        accuracy_m: null,
        label: `P${prev.length + 1}`,
      },
    ]);
  };

  const captureHere = async () => {
    setCapturing(true);
    try {
      const fix = await getCurrentPosition();
      if (vertices.length >= 64) {
        notify.warning('Maximum 64 boundary points.');
        return;
      }
      setVertices((prev) => [
        ...prev,
        {
          lat: Number(fix.lat.toFixed(7)),
          lng: Number(fix.lng.toFixed(7)),
          accuracy_m: fix.accuracy_m != null ? Math.round(fix.accuracy_m) : null,
          label: `P${prev.length + 1}`,
        },
      ]);
      notify.success(`Corner added (accuracy ${formatAccuracy(fix.accuracy_m)}).`);
    } catch (err) {
      notify.error(err.message || 'Unable to capture GPS.');
    } finally {
      setCapturing(false);
    }
  };

  const removeLast = () => setVertices((prev) => prev.slice(0, -1));
  const clearAll = () => setVertices([]);

  if (!canManage) {
    return (
      <div className="apex-card p-5">
        <h5 className="fw-bold">School boundary</h5>
        <p className="text-muted mb-0">Only the school admin can set campus GPS boundaries.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/settings" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> School settings
        </Link>
      </div>

      <PageHeader
        title="School boundary"
        subtitle="Draw the campus perimeter on OpenStreetMap (free). Staff sign-in and class attendance require being inside when enabled."
      />

      {isLoading ? (
        <div className="py-5 text-center"><ApexLoader label="Loading boundary…" /></div>
      ) : (
        <div className="row g-4">
          <div className="col-lg-8">
            <div className="apex-card p-3 p-md-4">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h6 className="fw-semibold mb-0 d-flex align-items-center gap-2">
                  <FiMapPin size={16} /> Map (click to place corners)
                </h6>
                <div className="d-flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                    disabled={capturing}
                    onClick={captureHere}
                  >
                    <FiCrosshair size={14} />
                    {capturing ? 'Locating…' : 'Add my GPS point'}
                  </button>
                  <button type="button" className="btn btn-outline-secondary btn-sm" disabled={!vertices.length} onClick={removeLast}>
                    Undo last
                  </button>
                  <button type="button" className="btn btn-outline-danger btn-sm" disabled={!vertices.length} onClick={clearAll}>
                    <FiTrash2 size={14} /> Clear
                  </button>
                </div>
              </div>
              <SchoolBoundaryMap
                vertices={vertices}
                onMapClick={addPointFromMap}
                interactive
                locateUser
                showUserMarker
                height={420}
              />
              <p className="form-text mb-0 mt-2">
                The map opens on <strong>your current GPS location</strong> so you can place corners while on campus.
                Use <strong>Map</strong>, <strong>Satellite</strong>, or <strong>Hybrid</strong> (top-right) to switch views — free, no API key.
                Place at least <strong>4 corners</strong> around the school compound.
              </p>
            </div>
          </div>

          <div className="col-lg-4">
            <div className="apex-card p-4 mb-3">
              <h6 className="fw-semibold mb-3">Boundary settings</h6>
              <div className="mb-3">
                <label className="form-label small fw-medium">Name</label>
                <input className="form-control form-control-sm" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Buffer (metres)</label>
                <input
                  type="number"
                  min={0}
                  max={500}
                  className="form-control form-control-sm"
                  value={bufferMeters}
                  onChange={(e) => setBufferMeters(e.target.value)}
                />
                <div className="form-text">Extra allowance outside the line for GPS drift (recommended 15–40 m).</div>
              </div>
              <div className="form-check form-switch mb-3">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="geofence-enabled"
                  checked={isEnabled}
                  onChange={(e) => setIsEnabled(e.target.checked)}
                />
                <label className="form-check-label small" htmlFor="geofence-enabled">
                  Enforce geofence for staff sign-in &amp; class attendance
                </label>
              </div>
              <button
                type="button"
                className="btn btn-primary w-100 d-inline-flex align-items-center justify-content-center gap-2"
                disabled={saveMutation.isPending || vertices.length < 4}
                onClick={() => saveMutation.mutate()}
              >
                <FiSave size={16} />
                {saveMutation.isPending ? 'Saving…' : 'Save boundary'}
              </button>
              {vertices.length < 4 && (
                <p className="text-warning small mt-2 mb-0">
                  Add {4 - vertices.length} more corner{4 - vertices.length === 1 ? '' : 's'} to save.
                </p>
              )}
            </div>

            <div className="apex-card p-4">
              <h6 className="fw-semibold mb-2">Corners ({vertices.length})</h6>
              {vertices.length === 0 ? (
                <p className="text-muted small mb-0">No points yet. Click the map or use “Add my GPS point”.</p>
              ) : (
                <div className="table-responsive" style={{ maxHeight: 280, overflowY: 'auto' }}>
                  <table className="table table-sm align-middle mb-0">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Lat</th>
                        <th>Lng</th>
                        <th>Accuracy</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vertices.map((v, i) => (
                        <tr key={`${v.lat}-${v.lng}-${i}`}>
                          <td>P{i + 1}</td>
                          <td className="font-monospace small">{Number(v.lat).toFixed(6)}</td>
                          <td className="font-monospace small">{Number(v.lng).toFixed(6)}</td>
                          <td className="small">{formatAccuracy(v.accuracy_m)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SchoolBoundarySettings;
