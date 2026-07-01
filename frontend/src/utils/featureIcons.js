import {
  FiHome, FiUsers, FiBriefcase, FiBook, FiCalendar, FiDollarSign,
  FiBookOpen, FiTruck, FiPackage, FiCreditCard, FiBarChart2, FiMessageSquare, FiGrid,
} from 'react-icons/fi';

const ICON_MAP = {
  FiHome, FiUsers, FiBriefcase, FiBook, FiCalendar, FiDollarSign,
  FiBookOpen, FiTruck, FiPackage, FiCreditCard, FiBarChart2, FiMessageSquare, FiGrid,
};

export function resolveFeatureIcon(name) {
  return ICON_MAP[name] || FiGrid;
}