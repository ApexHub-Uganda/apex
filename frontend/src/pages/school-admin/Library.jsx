import EntityListPage from '../../components/EntityListPage';
import { getEntityConfig } from '../../config/entityRegistry';

export function Library() {
  return (
    <EntityListPage
      title="Library"
      featureKey="library_management"
      config={getEntityConfig('library_management')}
    />
  );
}

export default Library;