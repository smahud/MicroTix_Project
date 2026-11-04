import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './app/App';
import { I18nProvider } from './i18n';
import { BrandingProvider } from './branding';
import { ApiProvider } from './api';
import { SessionProvider } from './state/session';
import { ToastProvider } from './design-system/primitives/Toast';

import './styles/tokens.css';
import './styles/base.css';
import './design-system/primitives/primitives.css';
import './design-system/components/components.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <BrandingProvider>
        <ApiProvider>
          <SessionProvider>
            <ToastProvider>
              <BrowserRouter>
                <App />
              </BrowserRouter>
            </ToastProvider>
          </SessionProvider>
        </ApiProvider>
      </BrandingProvider>
    </I18nProvider>
  </StrictMode>,
);
