import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { libraryService } from '../../services/moduleService';

const MOCK_LIBRARY = [
  { id: 1, title: 'Introduction to Physics', author: 'Halliday & Resnick', isbn: '978-0470469088', category: 'Science', copies: 12, available: 8 },
  { id: 2, title: 'Mathematics for Engineers', author: 'Kreyszig', isbn: '978-0470458365', category: 'Mathematics', copies: 10, available: 5 },
  { id: 3, title: 'World History', author: 'Spielvogel', isbn: '978-1305090195', category: 'History', copies: 8, available: 3 },
];

export function Library() {
  return (
    <ModulePage
      title="Library"
      subtitle="Manage books, issues, and returns"
      queryKey={['library']}
      fetchData={() => libraryService.list()}
      mockData={MOCK_LIBRARY}
      onCreate={(data) => libraryService.create(data)}
      createLabel="Add Book"
      columns={[
        { key: 'title', label: 'Title', accessor: 'title', sortable: true },
        { key: 'author', label: 'Author', accessor: 'author' },
        { key: 'isbn', label: 'ISBN', accessor: 'isbn' },
        { key: 'category', label: 'Category', accessor: 'category' },
        { key: 'copies', label: 'Copies', accessor: 'copies' },
        { key: 'available', label: 'Available', render: (row) => (
          <span className={row.available > 0 ? 'text-success fw-semibold' : 'text-danger fw-semibold'}>
            {row.available}
          </span>
        )},
      ]}
      formFields={[
        { name: 'title', label: 'Book Title', required: true },
        { name: 'author', label: 'Author', required: true },
        { name: 'isbn', label: 'ISBN', required: true },
        { name: 'category', label: 'Category', type: 'select', options: [
          { value: 'Science', label: 'Science' },
          { value: 'Mathematics', label: 'Mathematics' },
          { value: 'History', label: 'History' },
          { value: 'Literature', label: 'Literature' },
        ]},
        { name: 'copies', label: 'Number of Copies', type: 'number', required: true },
      ]}
    />
  );
}

export default Library;