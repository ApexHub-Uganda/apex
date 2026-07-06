import EntityListPage from '../../components/EntityListPage';
import { getEntityConfig } from '../../config/entityRegistry';

export function Payroll() {
  return (
    <EntityListPage
      title="Payroll"
      featureKey="payroll_runs"
      config={getEntityConfig('payroll_runs')}
    />
  );
}

export default Payroll;