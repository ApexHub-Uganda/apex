import { useParams } from 'react-router-dom';
import ModulePage from '../../components/ModulePage';
import { useTenant } from '../../hooks/useTenant';

export function SubModulePage({ title, subtitle, featureKey, createLabel = 'Add Record' }) {
  const params = useParams();
  const { isFeatureEnabled } = useTenant();
  const resolvedTitle = title || params.module?.replace(/-/g, ' ') || 'Module';
  const key = featureKey || params.featureKey;

  if (key && !isFeatureEnabled(key)) {
    return (
      <div className="apex-card p-5 text-center">
        <h5 className="fw-bold">Feature not on your plan</h5>
        <p className="text-muted mb-0">Upgrade your subscription to access {resolvedTitle}.</p>
      </div>
    );
  }

  return (
    <ModulePage
      title={resolvedTitle}
      subtitle={subtitle || `Manage ${resolvedTitle.toLowerCase()} records`}
      queryKey={['submodule', resolvedTitle, params]}
      fetchData={async () => []}
      createLabel={createLabel}
      onCreate={async () => ({})}
      columns={[
        { key: 'name', label: 'Name', accessor: 'name', sortable: true },
        { key: 'status', label: 'Status', accessor: 'status' },
        { key: 'updated', label: 'Updated', accessor: 'updated' },
      ]}
      formFields={[
        { name: 'name', label: 'Name', required: true },
        { name: 'notes', label: 'Notes', type: 'textarea' },
      ]}
    />
  );
}

export default SubModulePage;