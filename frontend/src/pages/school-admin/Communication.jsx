import EntityListPage from '../../components/EntityListPage';
import { getEntityConfig } from '../../config/entityRegistry';

export function Communication() {
  return (
    <EntityListPage
      title="Announcements"
      featureKey="announcements"
      config={getEntityConfig('announcements')}
    />
  );
}

export default Communication;