import {
  PARENT_CONTACT_LABELS,
  PARENT_RELATIONSHIP_LABELS,
  STAFF_CATEGORY_LABELS,
  STAFF_EMPLOYMENT_LABELS,
  STAFF_STATUS_LABELS,
  STUDENT_BOARDING_LABELS,
  STUDENT_GENDER_LABELS,
  STUDENT_STATUS_LABELS,
} from '../utils/categoryFilters';

export const STUDENT_DIRECTORY_FILTERS = [
  {
    key: 'class_name',
    label: 'Class',
    field: 'class_name',
    allLabel: 'All classes',
  },
  {
    key: 'stream_name',
    label: 'Stream',
    field: 'stream_name',
    allLabel: 'All streams',
  },
  {
    key: 'status',
    label: 'Status',
    field: 'status',
    allLabel: 'All statuses',
    labelMap: STUDENT_STATUS_LABELS,
  },
  {
    key: 'gender',
    label: 'Gender',
    field: 'gender',
    allLabel: 'All genders',
    labelMap: STUDENT_GENDER_LABELS,
  },
  {
    key: 'boarding_status',
    label: 'Boarding',
    field: 'boarding_status',
    allLabel: 'All boarding',
    labelMap: STUDENT_BOARDING_LABELS,
  },
  {
    key: 'profile',
    label: 'Profile',
    allLabel: 'All profiles',
    getValue: (row) => (row.is_profile_incomplete ? 'incomplete' : 'complete'),
    options: [
      { value: 'complete', label: 'Complete' },
      { value: 'incomplete', label: 'Incomplete' },
    ],
  },
];

export const STAFF_DIRECTORY_FILTERS = [
  {
    key: 'staff_category',
    label: 'Category',
    field: 'staff_category',
    allLabel: 'All categories',
    labelMap: STAFF_CATEGORY_LABELS,
  },
  {
    key: 'portal_role',
    label: 'Role',
    field: 'portal_role',
    allLabel: 'All roles',
    optionLabelField: 'role_label',
  },
  {
    key: 'department_name',
    label: 'Department',
    field: 'department_name',
    allLabel: 'All departments',
  },
  {
    key: 'employment_type',
    label: 'Employment',
    field: 'employment_type',
    allLabel: 'All employment',
    labelMap: STAFF_EMPLOYMENT_LABELS,
  },
  {
    key: 'status',
    label: 'Status',
    field: 'status',
    allLabel: 'All statuses',
    labelMap: STAFF_STATUS_LABELS,
  },
  {
    key: 'portal',
    label: 'Portal',
    allLabel: 'All portal',
    getValue: (row) => (row.has_user_account ? 'active' : 'none'),
    options: [
      { value: 'active', label: 'Portal active' },
      { value: 'none', label: 'No account' },
    ],
  },
];

export const PARENT_DIRECTORY_FILTERS = [
  {
    key: 'relationship_to_student',
    label: 'Relationship',
    field: 'relationship_to_student',
    allLabel: 'All relationships',
    labelMap: PARENT_RELATIONSHIP_LABELS,
  },
  {
    key: 'is_fee_payer',
    label: 'Fee payer',
    allLabel: 'All fee payers',
    getValue: (row) => (row.is_fee_payer ? 'yes' : 'no'),
    options: [
      { value: 'yes', label: 'Fee payer' },
      { value: 'no', label: 'Not fee payer' },
    ],
  },
  {
    key: 'preferred_contact_method',
    label: 'Contact',
    field: 'preferred_contact_method',
    allLabel: 'All contact methods',
    labelMap: PARENT_CONTACT_LABELS,
  },
  {
    key: 'county',
    label: 'District',
    field: 'county',
    allLabel: 'All districts',
  },
  {
    key: 'linked',
    label: 'Learners',
    allLabel: 'All parents',
    getValue: (row) => ((row.children_count || 0) > 0 ? 'linked' : 'unlinked'),
    options: [
      { value: 'linked', label: 'Has linked learners' },
      { value: 'unlinked', label: 'No learners linked' },
    ],
  },
];