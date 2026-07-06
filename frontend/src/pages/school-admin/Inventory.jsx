import EntityListPage from '../../components/EntityListPage';
import { getEntityConfig } from '../../config/entityRegistry';

export function Inventory() {
  return (
    <EntityListPage
      title="Inventory"
      featureKey="inventory_items"
      config={getEntityConfig('inventory_items')}
    />
  );
}

export default Inventory;