import './globals.css';
import './ui-refresh.css';

export const metadata = {
  title: 'Urban Furniture · Business OS',
  description: 'Role-aware furniture accounting workspace',
  icons: {
    icon: '/urban-furniture-logo.png',
    apple: '/urban-furniture-logo.png',
  },
};

export default function RootLayout({ children }) {
  return <html lang="en"><body>{children}</body></html>;
}
