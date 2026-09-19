import { Activity, BarChart3, Boxes, Calculator, FileCheck2, FileText, LayoutDashboard, ReceiptIndianRupee, Settings, ShoppingCart, Users, WalletCards } from 'lucide-react';

export const navigation = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard, roles: ['admin', 'accountant', 'contact'] },
  { href: '/documents', label: 'Invoices & bills', icon: FileText, roles: ['admin', 'accountant', 'contact'] },
  { href: '/orders', label: 'Sales & purchases', icon: ShoppingCart, roles: ['admin', 'accountant'] },
  { href: '/contacts', label: 'Contacts', icon: Users, roles: ['admin', 'accountant'] },
  { href: '/products', label: 'Products', icon: Boxes, roles: ['admin', 'accountant'] },
  { href: '/inventory', label: 'Inventory', icon: ReceiptIndianRupee, roles: ['admin', 'accountant'] },
  { href: '/expenses', label: 'Expenses', icon: WalletCards, roles: ['admin', 'accountant'] },
  { href: '/payments', label: 'Payments', icon: WalletCards, roles: ['admin', 'accountant', 'contact'] },
  { href: '/approvals', label: 'Payment approvals', icon: FileCheck2, roles: ['admin', 'accountant'] },
  { href: '/accounting', label: 'Accounting', icon: Calculator, roles: ['admin', 'accountant'] },
  { href: '/reports', label: 'Reports', icon: BarChart3, roles: ['admin', 'accountant'] },
  { href: '/activity', label: 'Activity', icon: Activity, roles: ['admin', 'accountant'] },
  { href: '/settings', label: 'Settings', icon: Settings, roles: ['admin', 'accountant', 'contact'] },
];

export const roleLabel = { admin: 'Admin workspace', accountant: 'Accountant workspace', contact: 'Partner portal' };
