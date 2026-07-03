import {
  FiHome, FiUsers, FiBriefcase, FiBook, FiCalendar, FiDollarSign,
  FiBookOpen, FiTruck, FiPackage, FiCreditCard, FiBarChart2, FiMessageSquare,
  FiGrid, FiUserPlus, FiAward, FiLifeBuoy, FiClock, FiEdit, FiFileText,
  FiLayers, FiLink, FiSettings, FiShield, FiMapPin, FiFile, FiHeart,
  FiCheckCircle, FiPercent, FiList, FiTrendingDown, FiRotateCcw, FiBookmark,
  FiMap, FiShoppingCart, FiTrendingUp, FiStar, FiBell, FiMail, FiSmartphone,
  FiRadio, FiUserCheck, FiDatabase, FiMessageCircle,
} from 'react-icons/fi';

const ICON_MAP = {
  FiHome, FiUsers, FiBriefcase, FiBook, FiCalendar, FiDollarSign,
  FiBookOpen, FiTruck, FiPackage, FiCreditCard, FiBarChart2, FiMessageSquare,
  FiGrid, FiUserPlus, FiAward, FiLifeBuoy, FiClock, FiEdit, FiFileText,
  FiLayers, FiLink, FiSettings, FiShield, FiMapPin, FiFile, FiHeart,
  FiCheckCircle, FiPercent, FiList, FiTrendingDown, FiRotateCcw, FiBookmark,
  FiMap, FiShoppingCart, FiTrendingUp, FiStar, FiBell, FiMail, FiSmartphone,
  FiRadio, FiUserCheck, FiDatabase, FiMessageCircle,
};

export function resolveFeatureIcon(name) {
  return ICON_MAP[name] || FiGrid;
}