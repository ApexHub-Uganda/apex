import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { inventoryService } from '../../services/moduleService';

const MOCK_INVENTORY = [
  { id: 1, item: 'Whiteboard Markers', category: 'Stationery', quantity: 120, unit: 'pcs', min_stock: 50, status: 'active' },
  { id: 2, item: 'A4 Paper Reams', category: 'Stationery', quantity: 35, unit: 'reams', min_stock: 20, status: 'active' },
  { id: 3, item: 'Lab Microscopes', category: 'Equipment', quantity: 8, unit: 'units', min_stock: 5, status: 'active' },
  { id: 4, item: 'Sports Balls', category: 'Sports', quantity: 3, unit: 'pcs', min_stock: 10, status: 'inactive' },
];

export function Inventory() {
  return (
    <ModulePage
      title="Inventory"
      subtitle="Track school supplies and equipment stock"
      queryKey={['inventory']}
      fetchData={() => inventoryService.list()}
      mockData={MOCK_INVENTORY}
      onCreate={(data) => inventoryService.create(data)}
      createLabel="Add Item"
      columns={[
        { key: 'item', label: 'Item', accessor: 'item', sortable: true },
        { key: 'category', label: 'Category', accessor: 'category' },
        { key: 'quantity', label: 'Quantity', render: (row) => `${row.quantity} ${row.unit}` },
        { key: 'min_stock', label: 'Min Stock', accessor: 'min_stock' },
        { key: 'status', label: 'Status', render: (row) => (
          <StatusBadge status={row.quantity <= row.min_stock ? 'inactive' : 'active'} />
        )},
      ]}
      formFields={[
        { name: 'item', label: 'Item Name', required: true },
        { name: 'category', label: 'Category', type: 'select', options: [
          { value: 'Stationery', label: 'Stationery' },
          { value: 'Equipment', label: 'Equipment' },
          { value: 'Sports', label: 'Sports' },
          { value: 'Furniture', label: 'Furniture' },
        ]},
        { name: 'quantity', label: 'Quantity', type: 'number', required: true },
        { name: 'unit', label: 'Unit', required: true },
        { name: 'min_stock', label: 'Minimum Stock', type: 'number', required: true },
      ]}
    />
  );
}

export default Inventory;