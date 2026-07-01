import { Toaster } from 'react-hot-toast';
import { useTheme } from '../hooks/useTheme';

export function AppToaster() {
  const { theme } = useTheme();

  return (
    <Toaster
      position="top-right"
      reverseOrder={false}
      gutter={10}
      containerStyle={{ top: 72, right: 16 }}
      toastOptions={{
        className: 'apex-toast',
        duration: 3800,
      }}
      theme={theme === 'dark' ? 'dark' : 'light'}
    />
  );
}

export default AppToaster;