import EntityListPage from '../../components/EntityListPage';
import { getEntityConfig } from '../../config/entityRegistry';

export function Transport() {
  return (
    <EntityListPage
      title="Transport Routes"
      featureKey="vehicles"
      config={getEntityConfig('vehicles')}
    />
  );
}

export default Transport;