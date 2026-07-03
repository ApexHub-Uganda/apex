import { useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import PlanEditorWorkspace from '../../components/PlanEditorWorkspace';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { plansService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

export function PlanEditor() {
  const { planId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const isNew = planId === 'new';

  const { data: plan, isLoading, isError } = useQuery({
    queryKey: ['plan-editor', planId],
    queryFn: () => plansService.get(planId),
    enabled: !isNew,
  });

  const returnTab = searchParams.get('tab') || 'plans';
  const returnPath = `/super-admin/plans${returnTab ? `?tab=${returnTab}` : ''}`;

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['plans-subscriptions-hub'] });
    queryClient.invalidateQueries({ queryKey: ['plans'] });
    queryClient.invalidateQueries({ queryKey: ['plans-manage'] });
    queryClient.invalidateQueries({ queryKey: ['plan-editor'] });
  };

  const handleCancel = () => navigate(returnPath);

  const handleSave = async (formData) => {
    setSaving(true);
    try {
      if (isNew) {
        await plansService.create({
          ...formData,
          slug: formData.slug || formData.name.toLowerCase().replace(/\s+/g, '_'),
        });
        notify.success('Plan created successfully.');
      } else {
        await plansService.update(planId, formData);
        notify.success('Plan updated successfully.');
      }
      invalidateAll();
      navigate(returnPath);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save plan.'));
    } finally {
      setSaving(false);
    }
  };

  if (!isNew && isLoading) return <PageSkeleton />;

  if (!isNew && isError) {
    return (
      <div className="apex-card p-5 text-center">
        <h5 className="fw-bold">Unable to load plan</h5>
        <p className="text-muted">The plan could not be loaded. It may have been removed.</p>
        <button type="button" className="btn btn-primary btn-sm" onClick={handleCancel}>
          Back to plans
        </button>
      </div>
    );
  }

  return (
    <PlanEditorWorkspace
      plan={isNew ? null : plan}
      onSave={handleSave}
      onCancel={handleCancel}
      saving={saving}
    />
  );
}

export default PlanEditor;