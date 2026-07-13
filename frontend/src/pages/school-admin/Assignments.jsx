import { Link } from 'react-router-dom';
import { FiArrowLeft, FiEdit, FiFileText, FiPercent } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import FeatureGate from '../../components/FeatureGate';

const WORKFLOWS = [
  {
    key: 'marks',
    featureKey: 'marks_entry',
    title: 'Marks entry',
    description: 'Name an assignment, enter student scores for your subjects and classes — no term required.',
    path: '/school-admin/academics/assignments/marks',
    icon: FiEdit,
  },
  {
    key: 'grades',
    featureKey: 'grade_calculation',
    title: 'Grade calculation',
    description: 'Apply a grading scheme to entered marks and generate letter grades for your class mark sheet.',
    path: '/school-admin/academics/assignments/grades',
    icon: FiPercent,
  },
];

export function Assignments() {
  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Academics
        </Link>
      </div>

      <PageHeader
        title="Assignments"
        subtitle="Track regular class assignments and student progress. Name each assessment, enter marks, then apply a grading scheme — subject and class choices follow your teaching assignments."
      />

      <div className="row g-3">
        {WORKFLOWS.map((workflow) => {
          const Icon = workflow.icon;
          return (
            <div key={workflow.key} className="col-md-6">
              <FeatureGate featureKey={workflow.featureKey}>
                <Link to={workflow.path} className="text-decoration-none">
                  <div className="apex-card p-4 h-100 assignment-workflow-card">
                    <div className="d-flex align-items-start gap-3">
                      <div className="assignment-workflow-icon">
                        <Icon size={20} />
                      </div>
                      <div>
                        <h5 className="fw-semibold mb-1">{workflow.title}</h5>
                        <p className="text-muted small mb-0">{workflow.description}</p>
                      </div>
                    </div>
                  </div>
                </Link>
              </FeatureGate>
            </div>
          );
        })}
      </div>

      <div className="apex-card p-3 p-md-4 mt-4">
        <div className="d-flex align-items-center gap-2 text-muted small">
          <FiFileText size={14} />
          <span>
            Homework and class assignment tasks are listed separately under Academics if your school uses them.
          </span>
        </div>
      </div>
    </div>
  );
}

export default Assignments;