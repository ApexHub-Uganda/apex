import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { plansService } from '../../services/moduleService';

export function Plans() {
  return (
    <ModulePage
      title="Subscription Plans"
      subtitle="Configure pricing plans and feature tiers"
      queryKey={['plans']}
      fetchData={() => plansService.list({ page_size: 50 })}
      onCreate={(data) => plansService.create({
        name: data.name,
        slug: data.slug,
        description: data.description,
        price_monthly: data.price_monthly,
        price_yearly: data.price_yearly || Number(data.price_monthly) * 10,
        max_students: 0,
        max_staff: 0,
        max_parents: 0,
        is_active: true,
        is_public: true,
      })}
      onUpdate={(id, data) => plansService.update(id, {
        name: data.name,
        description: data.description,
        price_monthly: data.price_monthly,
        price_yearly: data.price_yearly,
        max_students: 0,
        max_staff: 0,
        max_parents: 0,
        is_active: data.is_active !== 'false',
        is_public: data.is_public !== 'false',
      })}
      onDelete={(id) => plansService.delete(id)}
      createLabel="Create Plan"
      columns={[
        { key: 'name', label: 'Plan Name', accessor: 'name', sortable: true },
        { key: 'slug', label: 'Slug', accessor: 'slug' },
        { key: 'price_monthly', label: 'Monthly', render: (row) => `$${Number(row.price_monthly).toFixed(2)}` },
        { key: 'price_yearly', label: 'Yearly', render: (row) => `$${Number(row.price_yearly).toFixed(2)}` },
        { key: 'is_active', label: 'Status', render: (row) => <StatusBadge status={row.is_active ? 'active' : 'inactive'} /> },
        { key: 'features', label: 'Features', render: (row) => (row.features?.length ? row.features.slice(0, 3).join(', ') + (row.features.length > 3 ? '…' : '') : '—') },
      ]}
      formFields={[
        { name: 'name', label: 'Plan Name', required: true },
        { name: 'slug', label: 'Slug', required: true, placeholder: 'e.g. premium' },
        { name: 'description', label: 'Description', type: 'textarea' },
        { name: 'price_monthly', label: 'Monthly Price ($)', type: 'number', required: true },
        { name: 'price_yearly', label: 'Yearly Price ($)', type: 'number' },
      ]}
    />
  );
}

export default Plans;