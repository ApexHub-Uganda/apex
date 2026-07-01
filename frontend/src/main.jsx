import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'sweetalert2/dist/sweetalert2.min.css';
import './styles/global.css';
import './styles/themes.css';
import './styles/notify.css';
import App from './App';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
);