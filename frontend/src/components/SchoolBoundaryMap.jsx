import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup, Circle, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getCurrentPosition } from '../utils/geolocation';

// Fix default marker icons under Vite bundling
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

/** Blue pin for admin boundary editor "you are here". */
const youAreHereIconBlue = L.divIcon({
  className: 'school-boundary-you-are-here',
  html: `<div style="
    width:16px;height:16px;border-radius:50%;
    background:#2563eb;border:3px solid #fff;
    box-shadow:0 0 0 2px rgba(37,99,235,.35),0 2px 6px rgba(0,0,0,.25);
  "></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

/** Red pointer for staff attendance current location (live GPS). */
const youAreHereIconRed = L.divIcon({
  className: 'school-boundary-you-are-here-red',
  html: `<div style="
    width:18px;height:18px;border-radius:50%;
    background:#dc2626;border:3px solid #fff;
    box-shadow:0 0 0 3px rgba(220,38,38,.35),0 2px 8px rgba(0,0,0,.35);
  "></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

// Neutral world fallback only if GPS is unavailable (never used as the preferred open view)
const GPS_FALLBACK_CENTER = [0.3476, 32.5825];
const USER_ZOOM = 17;

const BASEMAP_STORAGE_KEY = 'apex.schoolBoundary.basemap';

/** Free basemaps — no API keys required. */
export const BASEMAP_LAYERS = {
  streets: {
    id: 'streets',
    label: 'Map',
    title: 'Street map',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  },
  satellite: {
    id: 'satellite',
    label: 'Satellite',
    title: 'Live satellite imagery',
    // Esri World Imagery — free for non-commercial / fair-use web apps with attribution
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution:
      'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
    maxZoom: 19,
  },
  hybrid: {
    id: 'hybrid',
    label: 'Hybrid',
    title: 'Satellite with place names',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution:
      'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
    maxZoom: 19,
    // Free labels overlay on satellite
    labelsUrl:
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    labelsAttribution: 'Labels &copy; Esri',
  },
};

const BASEMAP_ORDER = ['streets', 'satellite', 'hybrid'];

function readStoredBasemap() {
  try {
    const raw = localStorage.getItem(BASEMAP_STORAGE_KEY);
    if (raw && BASEMAP_LAYERS[raw]) return raw;
  } catch {
    // ignore private-mode storage errors
  }
  return 'streets';
}

function MapClickHandler({ onMapClick, enabled }) {
  useMapEvents({
    click(e) {
      if (!enabled) return;
      onMapClick?.({
        lat: e.latlng.lat,
        lng: e.latlng.lng,
      });
    },
  });
  return null;
}

function FitBounds({ vertices, userPosition, includeUser = false }) {
  const map = useMap();
  const lastFitKey = useRef('');
  useEffect(() => {
    const pts = (vertices || []).map((v) => [Number(v.lat), Number(v.lng)]);
    const hasUser = includeUser && userPosition?.lat != null && userPosition?.lng != null;
    if (hasUser) {
      pts.push([Number(userPosition.lat), Number(userPosition.lng)]);
    }
    if (!pts.length) return;
    // Fit when polygon changes, or once when user first appears (not on every GPS tick)
    const key = `${vertices?.length || 0}:${hasUser ? 'u' : 'n'}`;
    if (key === lastFitKey.current && !hasUser) return;
    if (key === lastFitKey.current && hasUser && lastFitKey.current.endsWith(':u')) {
      // already fitted with user — skip continuous re-zoom
      return;
    }
    lastFitKey.current = key;
    if (pts.length === 1) {
      map.setView(pts[0], USER_ZOOM, { animate: true });
      return;
    }
    const bounds = L.latLngBounds(pts);
    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.2));
    }
  }, [map, vertices, includeUser, userPosition?.lat, userPosition?.lng]);
  return null;
}

/** Keep map centered on live user when following. */
function FollowUser({ position, enabled, zoom = USER_ZOOM }) {
  const map = useMap();
  useEffect(() => {
    if (!enabled || position?.lat == null || position?.lng == null) return;
    map.panTo([position.lat, position.lng], { animate: true });
  }, [map, enabled, position?.lat, position?.lng, zoom]);
  return null;
}

/**
 * Read the current user's GPS.
 * When `panToUser` is true (no boundary corners yet), the map centers on them.
 * When false, only reports the fix for a "you are here" marker (polygon stays in view).
 */
function LocateUserGps({
  enabled,
  panToUser = true,
  zoom = USER_ZOOM,
  onLocated,
  onLocateError,
}) {
  const map = useMap();

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;

    getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 20000,
      // Allow a short-lived cached fix so the map opens quickly
      maximumAge: 30_000,
    })
      .then((fix) => {
        if (cancelled) return;
        if (panToUser) {
          map.setView([fix.lat, fix.lng], zoom, { animate: true });
        }
        onLocated?.(fix);
      })
      .catch((err) => {
        if (cancelled) return;
        onLocateError?.(err);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, panToUser, map, zoom, onLocated, onLocateError]);

  return null;
}

function BasemapSwitcher({ value, onChange }) {
  return (
    <div
      className="school-boundary-basemap-switcher btn-group shadow-sm"
      role="group"
      aria-label="Map base layer"
      style={{ zIndex: 1000 }}
    >
      {BASEMAP_ORDER.map((id) => {
        const layer = BASEMAP_LAYERS[id];
        const active = value === id;
        return (
          <button
            key={id}
            type="button"
            title={layer.title}
            className={`btn btn-sm ${active ? 'btn-primary' : 'btn-light'}`}
            aria-pressed={active}
            onClick={() => onChange(id)}
          >
            {layer.label}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Free OpenStreetMap + Leaflet campus boundary editor / viewer.
 *
 * Default open position: the signed-in user's current GPS location
 * (when no vertices are drawn yet). Existing polygons still fit-bounds.
 * Basemap: Map (OSM) / Satellite / Hybrid — free, no API key.
 */
export function SchoolBoundaryMap({
  vertices = [],
  onMapClick,
  interactive = true,
  height = 360,
  center,
  zoom = 15,
  /** When true (default for interactive maps), pan to user GPS if no corners yet */
  locateUser = true,
  showUserMarker = true,
  /** Controlled live position from parent (staff attendance). Overrides internal locate. */
  userPosition = null,
  /** Marker color: 'red' for staff live pin, 'blue' for admin editor */
  userMarkerColor = 'blue',
  /** Fit map to polygon + user pin together */
  fitUserWithBoundary = false,
  /** Gently pan toward live user (staff map) */
  followUser = false,
  /** Show Map / Satellite / Hybrid switcher (default true) */
  showBasemapSwitcher = true,
  /** Initial basemap: streets | satellite | hybrid */
  defaultBasemap,
}) {
  const [userFix, setUserFix] = useState(null);
  const [locateStatus, setLocateStatus] = useState('idle'); // idle | locating | ok | failed
  const [basemap, setBasemap] = useState(() => {
    if (defaultBasemap && BASEMAP_LAYERS[defaultBasemap]) return defaultBasemap;
    return readStoredBasemap();
  });

  const layer = BASEMAP_LAYERS[basemap] || BASEMAP_LAYERS.streets;
  const displayUser = userPosition?.lat != null ? userPosition : userFix;
  const userIcon = userMarkerColor === 'red' ? youAreHereIconRed : youAreHereIconBlue;
  const accuracyColor = userMarkerColor === 'red' ? '#dc2626' : '#2563eb';
  const accuracyFill = userMarkerColor === 'red' ? '#ef4444' : '#3b82f6';

  const handleBasemapChange = useCallback((id) => {
    if (!BASEMAP_LAYERS[id]) return;
    setBasemap(id);
    try {
      localStorage.setItem(BASEMAP_STORAGE_KEY, id);
    } catch {
      // ignore
    }
  }, []);

  const positions = useMemo(
    () => (vertices || []).map((v) => [Number(v.lat), Number(v.lng)]),
    [vertices],
  );

  const hasVertices = positions.length >= 1;
  // Prefer user GPS as initial center once known; else optional prop; else neutral fallback
  const initialCenter = useMemo(() => {
    if (displayUser) return [displayUser.lat, displayUser.lng];
    if (Array.isArray(center) && center.length === 2) return center;
    if (positions.length) return positions[0];
    return GPS_FALLBACK_CENTER;
  }, [displayUser, center, positions]);

  // Internal GPS only when parent is not driving position
  const shouldLocateUser = Boolean(locateUser) && !userPosition && !hasVertices;
  const shouldLocateWithBoundary = Boolean(locateUser) && !userPosition && hasVertices && showUserMarker;

  // Brighter polygon outline on dark satellite tiles
  const isSatellite = basemap === 'satellite' || basemap === 'hybrid';
  const polygonOptions = useMemo(() => (
    isSatellite
      ? {
          color: '#fbbf24',
          weight: 3,
          fillColor: '#fbbf24',
          fillOpacity: 0.22,
        }
      : {
          color: '#0f766e',
          weight: 2,
          fillColor: '#0f766e',
          fillOpacity: 0.18,
        }
  ), [isSatellite]);

  useEffect(() => {
    if (!shouldLocateUser) return;
    setLocateStatus('locating');
  }, [shouldLocateUser]);

  const handleLocated = useCallback((fix) => {
    setUserFix(fix);
    setLocateStatus('ok');
  }, []);

  const handleLocateError = useCallback(() => {
    setLocateStatus('failed');
  }, []);

  return (
    <div className="school-boundary-map border rounded overflow-hidden position-relative" style={{ height }}>
      {shouldLocateUser && locateStatus === 'locating' && (
        <div
          className="position-absolute top-0 start-0 end-0 px-2 py-1 small text-center text-bg-dark bg-opacity-75 text-white"
          style={{ zIndex: 1000 }}
        >
          Locating your position…
        </div>
      )}
      {shouldLocateUser && locateStatus === 'failed' && (
        <div
          className="position-absolute top-0 start-0 end-0 px-2 py-1 small text-center text-bg-warning"
          style={{ zIndex: 1000 }}
        >
          Could not read GPS — allow location access, or pan the map manually.
        </div>
      )}

      {showBasemapSwitcher && (
        <div
          className="position-absolute"
          style={{
            zIndex: 1000,
            top: shouldLocateUser && (locateStatus === 'locating' || locateStatus === 'failed') ? 32 : 10,
            right: 10,
          }}
        >
          <BasemapSwitcher value={basemap} onChange={handleBasemapChange} />
        </div>
      )}

      <MapContainer
        center={initialCenter}
        zoom={userFix && !hasVertices ? USER_ZOOM : zoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom
      >
        {/* key forces clean tile swap when basemap changes */}
        <TileLayer
          key={`base-${layer.id}`}
          attribution={layer.attribution}
          url={layer.url}
          maxZoom={layer.maxZoom || 19}
        />
        {layer.labelsUrl && (
          <TileLayer
            key={`labels-${layer.id}`}
            attribution={layer.labelsAttribution || ''}
            url={layer.labelsUrl}
            maxZoom={layer.maxZoom || 19}
            opacity={0.9}
          />
        )}
        <MapClickHandler onMapClick={onMapClick} enabled={interactive} />
        {shouldLocateUser && (
          <LocateUserGps
            enabled
            panToUser
            zoom={USER_ZOOM}
            onLocated={handleLocated}
            onLocateError={handleLocateError}
          />
        )}
        {shouldLocateWithBoundary && !userFix && (
          <LocateUserGps
            enabled
            panToUser={false}
            onLocated={handleLocated}
            onLocateError={() => {}}
          />
        )}
        {positions.length >= 3 && (
          <Polygon
            positions={positions}
            pathOptions={polygonOptions}
          />
        )}
        {(vertices || []).map((v, idx) => (
          <Marker key={`${v.lat}-${v.lng}-${idx}`} position={[v.lat, v.lng]}>
            <Popup>
              <strong>P{idx + 1}</strong>
              <br />
              {Number(v.lat).toFixed(6)}, {Number(v.lng).toFixed(6)}
              {v.accuracy_m != null && (
                <>
                  <br />
                  GPS accuracy: ±{Math.round(Number(v.accuracy_m))} m
                </>
              )}
            </Popup>
          </Marker>
        ))}
        {showUserMarker && displayUser && (
          <>
            {displayUser.accuracy_m != null && Number(displayUser.accuracy_m) > 0 && (
              <Circle
                center={[displayUser.lat, displayUser.lng]}
                radius={Math.min(Number(displayUser.accuracy_m), 400)}
                pathOptions={{
                  color: accuracyColor,
                  weight: 1,
                  fillColor: accuracyFill,
                  fillOpacity: 0.12,
                }}
              />
            )}
            <Marker position={[displayUser.lat, displayUser.lng]} icon={userIcon} zIndexOffset={1000}>
              <Popup>
                <strong>You are here</strong>
                <br />
                {Number(displayUser.lat).toFixed(6)}, {Number(displayUser.lng).toFixed(6)}
                {displayUser.accuracy_m != null && (
                  <>
                    <br />
                    Accuracy: ±{Math.round(Number(displayUser.accuracy_m))} m
                  </>
                )}
              </Popup>
            </Marker>
          </>
        )}
        {followUser && displayUser && (
          <FollowUser position={displayUser} enabled zoom={USER_ZOOM} />
        )}
        {positions.length >= 2 && (
          <FitBounds
            vertices={vertices}
            userPosition={fitUserWithBoundary ? displayUser : null}
            includeUser={Boolean(fitUserWithBoundary && displayUser)}
          />
        )}
      </MapContainer>
    </div>
  );
}

export default SchoolBoundaryMap;
